"""Ciclo di monitoraggio: punteggi ogni minuto, quote a pagamento solo quando servono,
archiviazione completa (anche in DRY_RUN), risoluzione esiti e alert calibrati."""
from __future__ import annotations

import json
import logging
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config
from .decision import Evaluation, Quote, evaluate, match_state
from .engine import Market, Match, final_winner, map_outcome, name_match, parse_allsports_odds, parse_market, \
    parse_match, parse_timestamp
from .feeds import AllSports, FeedError, Telegram, TheOddsAPI
from .model import EmpiricalModel
from .storage import Storage

LOG = logging.getLogger("odds-monitor")
ROME = ZoneInfo("Europe/Rome")
SPORTS = ("tennis", "football", "basketball")
LIVE_WINDOW = {"tennis": timedelta(hours=6), "football": timedelta(hours=3), "basketball": timedelta(hours=4)}


def sport_for_key(key: str) -> str | None:
    if key.startswith("tennis_"):
        return "tennis"
    if key.startswith("soccer_"):
        return "football"
    if key.startswith("basketball_"):
        return "basketball"
    return None


def trusted_context(path: str, match: Match, now: datetime) -> dict:
    """Solo attestazioni recenti (<24h), con link HTTPS; altrimenti informazioni sconosciute."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        item = data.get(f"{match.sport}:{match.event_id}", {})
        if not isinstance(item, dict):
            return {}
        stamped = datetime.fromisoformat(str(item.get("verified_at", "")).replace("Z", "+00:00"))
        if stamped.tzinfo is None or not timedelta(0) <= now - stamped <= timedelta(hours=24):
            return {}
        sources = item.get("sources", [])
        if not isinstance(sources, list) or not sources or not all(isinstance(x, str) and x.startswith("https://") for x in sources):
            return {}
        if item.get("injury") not in {"clear", "confirmed"} or item.get("fatigue") not in {"low", "high"}:
            return {}
        return item
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def orient(match: Match, market_first: str, prob: dict[str, float], prices: dict[str, float], books: int,
           spread: float, source: str) -> Quote:
    """Riporta quote di un mercato (ordine casa/ospite del bookmaker) all'ordine del livescore."""
    p, q = {}, {}
    for side in ("first", "second"):
        key = map_outcome(match, market_first, side)
        if key in prob:
            p[side] = prob[key]
        if key in prices:
            q[side] = prices[key]
    if "draw" in prob:
        p["draw"] = prob["draw"]
    if "draw" in prices:
        q["draw"] = prices["draw"]
    return Quote(p, q, books, spread, source)


def format_alert(ev: Evaluation, now: datetime, dry_run: bool) -> str:
    m, est = ev.match, ev.estimate
    when = now.astimezone(ROME).strftime("%d/%m/%Y %H:%M:%S %Z")
    target = m.first if ev.target == "first" else m.second
    fair = f"{1 / ev.final:.2f}" if ev.final else "n/d"
    live_price = f"{ev.live_price:.2f}" if ev.live_price else "n/d"
    edge = f"{ev.live_price * ev.final - 1:+.1%}" if ev.final and ev.live_price else "n/d"
    lines = [
        f"{'[SIMULAZIONE] ' if dry_run else ''}POSSIBILE RIMONTA — {m.sport.upper()}",
        f"{m.competition or 'Competizione da verificare'}",
        f"{m.first} - {m.second}",
        f"Punteggio: {m.score} | fase: {m.phase}",
        f"Ora Italia: {when}",
        f"Favorito in svantaggio: {target} | esito: {ev.label}",
        (f"PROBABILITÀ FINALE: {ev.final:.1%} (stima prudente {ev.final_lower:.1%})"
         if ev.final is not None else "Probabilità finale: n/d"),
        (f"  = media fra storico {est.point:.1%} (limite inferiore {est.lower:.1%}, campione {est.n}, "
         f"stato {ev.state}) e mercato live {ev.live_prob:.1%}" if est and ev.live_prob is not None else
         f"  = solo storico {est.point:.1%} (campione {est.n}, stato {ev.state})" if est else ""),
        f"Quota live mediana: {live_price} | quota equa modello: {fair} | margine atteso: {edge}",
        "Evidenze: " + "; ".join(ev.evidence),
        "Fonti dati: AllSports (punteggi, quote pre), The Odds API (quote live). Non è una garanzia di esito.",
    ]
    return "\n".join(lines)


class Monitor:
    def __init__(self, cfg: Config, *, storage: Storage | None = None, allsports=None, odds=None, telegram=None):
        cfg.validate(live=storage is None)
        self.cfg = cfg
        self.db = storage or Storage(cfg.db_path)
        self.all = allsports or AllSports(cfg.allsports_key)
        self.odds = odds if odds is not None else (TheOddsAPI(cfg.odds_key, cfg.regions) if cfg.odds_key else None)
        self.telegram = telegram or (Telegram(cfg.telegram_token, cfg.telegram_chat) if not cfg.dry_run else None)
        self.stopped = False
        self.events: dict[str, tuple[datetime, list[dict]]] = {}
        self.last_odds_fetch: dict[str, datetime] = {}
        self.last_allsports_odds: dict[str, datetime] = {}
        self.last_score: dict[str, str] = {}
        self.dry_alerted: set[str] = set()
        self.last_resolve = datetime.min.replace(tzinfo=timezone.utc)
        self.model_loaded = datetime.min.replace(tzinfo=timezone.utc)
        self.reload_model()

    # --- modello ---------------------------------------------------------------------------
    def reload_model(self):
        self.model = EmpiricalModel(self.db.history(), bandwidth=self.cfg.model_bandwidth,
                                    min_sample=self.cfg.model_min_sample, z=self.cfg.model_z)
        self.approved = self.db.approved()
        self.model_loaded = datetime.now(timezone.utc)
        LOG.info("Modello: %d stati storici, %d stati/esiti promossi dalla validazione",
                 len(self.model.size), len(self.approved))

    def stop(self, *_):
        self.stopped = True

    # --- raccolta ---------------------------------------------------------------------------
    def fetch_scores(self) -> list[Match]:
        matches: list[Match] = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {pool.submit(self.all.live, sport): sport for sport in SPORTS}
            for job in as_completed(jobs):
                sport = jobs[job]
                try:
                    records = job.result()
                except (FeedError, ValueError, OSError) as exc:
                    LOG.warning("Livescore %s indisponibile: %s", sport, exc)
                    continue
                matches += [m for raw in records if (m := parse_match(sport, raw, require_behind=False))]
        return matches

    def archive_scores(self, matches: list[Match], now: datetime):
        for m in matches:
            key = f"{m.sport}:{m.event_id}"
            stamp = f"{m.score}|{m.phase}"
            if self.last_score.get(key) != stamp:
                self.last_score[key] = stamp
                self.db.snapshot_score(key, now, m.score, m.phase, {
                    "first": m.first, "second": m.second, "competition": m.competition, "category": m.category,
                    "sets": m.sets, "games": m.games, "goals": m.goals, "minute": m.minute, "behind": m.behind})

    def refresh_allsports_odds(self, live_keys: set[str], now: datetime):
        if not self.cfg.use_allsports_odds:
            return
        today = now.astimezone(ROME).date()
        for sport in SPORTS:
            last = self.last_allsports_odds.get(sport)
            if last and (now - last).total_seconds() < self.cfg.prematch_refresh:
                continue
            self.last_allsports_odds[sport] = now
            try:
                raw = self.all.odds(sport, today, today + timedelta(days=1))
            except (FeedError, ValueError, OSError) as exc:
                LOG.warning("Quote pre-partita AllSports %s indisponibili: %s", sport, exc)
                continue
            stored = 0
            for key, (prob, prices, books, spread) in parse_allsports_odds(
                    sport, raw, self.cfg.min_books, self.cfg.max_spread).items():
                if f"{sport}:{key}" in live_keys:
                    continue  # partita già iniziata: non aggiornare la quota "pre"
                self.db.store_pre(f"as:{sport}:{key}", {**prob, "_books": books, "_spread": spread}, now, prices,
                                  source="allsports")
                stored += 1
            LOG.info("Quote pre AllSports %s: %d eventi aggiornati", sport, stored)

    def odds_keys(self) -> list[str]:
        assert self.odds is not None
        keys = self.odds.active_keys(self.cfg.watch_keys)
        fixed = [k for k in keys if not k.startswith("tennis_") or k in self.cfg.watch_keys]
        tennis = [k for k in keys if k not in fixed][: self.cfg.auto_tennis_limit]
        return fixed + tennis

    def refresh_events(self, keys: list[str], now: datetime):
        assert self.odds is not None
        for key in keys:
            cached = self.events.get(key)
            if cached and (now - cached[0]).total_seconds() < self.cfg.events_refresh:
                continue
            try:
                self.events[key] = (now, self.odds.events(key))   # gratuito secondo la documentazione
            except (FeedError, ValueError, OSError) as exc:
                LOG.warning("Calendario %s indisponibile: %s", key, exc)

    def odds_plan(self, keys: list[str], trailing: list[Match], now: datetime) -> list[tuple[str, list[str] | None]]:
        """Decide quali chiamate a pagamento fare in questo ciclo.

        - live: solo per eventi iniziati che corrispondono a una partita con qualcuno in svantaggio;
        - pre: al massimo una volta ogni PREMATCH_REFRESH_SECONDS per campionati con eventi nelle 24h.
        """
        plan: list[tuple[str, list[str] | None]] = []
        for key in keys:
            sport = sport_for_key(key)
            events = self.events.get(key, (now, []))[1]
            live_ids, upcoming = [], False
            for e in events:
                start = parse_timestamp(e.get("commence_time", ""))
                if not start or not sport:
                    continue
                if now - LIVE_WINDOW[sport] < start <= now and any(
                        m.sport == sport and self._names_match(m, e) and self._worth_live_odds(m, e) for m in trailing):
                    live_ids.append(str(e.get("id")))
                elif now < start <= now + timedelta(hours=24):
                    upcoming = True
            last = self.last_odds_fetch.get(key)
            pre_due = upcoming and (not last or (now - last).total_seconds() >= self.cfg.prematch_refresh)
            if live_ids or pre_due:
                plan.append((key, None if pre_due else live_ids))
        # Le chiamate live hanno priorità sul budget rispetto a quelle pre-partita.
        plan.sort(key=lambda item: item[1] is None)
        return plan

    def _worth_live_odds(self, m: Match, event: dict) -> bool:
        """Spende crediti live solo se chi è sotto era il favorito e lo stato è modellabile
        (salvo COLLECT_ALL_LIVE_ODDS=true, utile solo per raccogliere dati con budget ampio)."""
        if self.cfg.collect_all_live_odds:
            return True
        stored, _, _ = self._load_pre(f"odds:{event.get('id')}")
        pre = orient(m, str(event.get("home_team", "")), stored, {}, 0, 0, "") if stored else None
        if pre is None:
            stored, _, _ = self._load_pre(f"as:{m.sport}:{m.event_id}")
            pre = Quote(stored, {}) if stored else None
        if not pre or pre.prob.get(m.behind or "", 0) < self.cfg.min_pre_probability:
            return False
        return match_state(m, self.cfg)[1] is None

    @staticmethod
    def _names_match(m: Match, event: dict) -> bool:
        t = m.sport == "tennis"
        h, a = str(event.get("home_team", "")), str(event.get("away_team", ""))
        return ((name_match(m.first, h, t) and name_match(m.second, a, t)) or
                (name_match(m.first, a, t) and name_match(m.second, h, t)))

    def fetch_odds(self, plan, now: datetime) -> dict[str, Market]:
        assert self.odds is not None
        today = now.astimezone(ROME).strftime("%Y-%m-%d")
        cost = self.odds.odds_cost()
        live_markets: dict[str, Market] = {}
        for key, event_ids in plan:
            if not self.db.available_budget(today, self.cfg.max_requests_day, cost):
                LOG.warning("Budget quote giornaliero esaurito (%d): chiamate sospese fino a domani",
                            self.cfg.max_requests_day)
                break
            self.db.consume(today, cost)   # prenota prima: evita di sforare in caso di crash
            try:
                records = self.odds.odds(key, event_ids)
            except (FeedError, ValueError, OSError) as exc:
                LOG.warning("Quote %s indisponibili: %s", key, exc)
                continue
            if event_ids is None:
                self.last_odds_fetch[key] = now
            sport = sport_for_key(key)
            if not sport:
                continue
            for raw in records:
                pre = parse_market(raw, sport, now, 86400, self.cfg.min_books)
                if pre and pre.starts_at > now + timedelta(minutes=2):
                    self.db.store_pre(f"odds:{pre.event_id}", {**pre.prob, "_books": pre.count, "_spread": pre.spread},
                                      now, pre.reference_odds, source="the-odds-api")
                    self.db.snapshot_odds(pre.event_id, "the-odds-api", now, pre.starts_at, "pre", pre.first,
                                          pre.second, pre.prob, pre.reference_odds, pre.count, pre.spread)
                live = parse_market(raw, sport, now, self.cfg.max_odds_age, self.cfg.min_books)
                if live and now - LIVE_WINDOW[sport] < live.starts_at <= now:
                    live_markets[live.event_id] = live
                    self.db.snapshot_odds(live.event_id, "the-odds-api", now, live.starts_at, "live", live.first,
                                          live.second, live.prob, live.reference_odds, live.count, live.spread)
        if self.odds.remaining is not None:
            self.db.set_kv("odds_api_remaining", str(self.odds.remaining))
        return live_markets

    # --- valutazione ------------------------------------------------------------------------
    def quotes_for(self, match: Match, live_markets: dict[str, Market], now: datetime) -> tuple[Quote | None, Quote | None]:
        """Quota pre (The Odds API se abbinata in modo univoco, altrimenti AllSports per event_key) e live."""
        candidates = []
        for key, (_, events) in self.events.items():
            if sport_for_key(key) != match.sport:
                continue
            for e in events:
                start = parse_timestamp(e.get("commence_time", ""))
                if start and now - LIVE_WINDOW[match.sport] < start <= now and self._names_match(match, e):
                    candidates.append(e)
        pre = live = None
        if len(candidates) == 1:   # nomi ambigui => nessun abbinamento
            e = candidates[0]
            event_id, home = str(e.get("id")), str(e.get("home_team", ""))
            stored, books, spread = self._load_pre(f"odds:{event_id}")
            if stored:
                pre = orient(match, home, stored, self.db.pre_prices(f"odds:{event_id}"), books, spread,
                             "The Odds API")
            market = live_markets.get(event_id)
            if market and market.spread <= self.cfg.max_spread:
                live = orient(match, market.first, market.prob, market.reference_odds, market.count, market.spread,
                              "The Odds API")
        if pre is None:
            stored, books, spread = self._load_pre(f"as:{match.sport}:{match.event_id}")
            if stored:
                pre = Quote(stored, self.db.pre_prices(f"as:{match.sport}:{match.event_id}"), books, spread,
                            "AllSports")
        return pre, live

    def _load_pre(self, event_id: str) -> tuple[dict[str, float] | None, int, float]:
        stored = self.db.pre(event_id)
        if not stored:
            return None, 0, 0.0
        books, spread = int(stored.pop("_books", 0)), float(stored.pop("_spread", 0.0))
        return stored, books, spread

    def evaluate_all(self, trailing: list[Match], live_markets: dict[str, Market], now: datetime) -> list[Evaluation]:
        alerts: list[Evaluation] = []
        for match in trailing:
            key = f"{match.sport}:{match.event_id}"
            if self.db.already_alerted(key) or key in self.dry_alerted:
                continue
            pre, live = self.quotes_for(match, live_markets, now)
            ctx = trusted_context(self.cfg.context_file, match, now)
            evaluations = evaluate(match, pre, live, self.model, self.approved, self.cfg, ctx)
            for ev in evaluations:
                self.db.record_evaluation(ev.as_row(), now)
            chosen = [ev for ev in evaluations if ev.decision == "alert"]
            if chosen:
                alerts.append(next((ev for ev in chosen if ev.outcome == "win"), chosen[0]))
        self.db.commit()
        return alerts

    def dispatch(self, alerts: list[Evaluation], now: datetime):
        for ev in alerts:
            key = f"{ev.match.sport}:{ev.match.event_id}"
            message = format_alert(ev, now, self.cfg.dry_run)
            if self.cfg.dry_run:
                self.dry_alerted.add(key)
                LOG.info("CANDIDATO (DRY_RUN, nessun invio):\n%s", message)
                continue
            try:
                assert self.telegram
                self.telegram.send(message)
            except (FeedError, ValueError, OSError) as exc:
                LOG.error("Invio Telegram non riuscito: %s", exc)
                continue
            self.db.mark_sent(key, ev.outcome, ev.state, now)
            LOG.info("Segnalazione inviata: %s", key)

    # --- esiti finali -----------------------------------------------------------------------
    def resolve_results(self, now: datetime):
        if (now - self.last_resolve).total_seconds() < 3600:
            return
        self.last_resolve = now
        pending = self.db.unresolved(now - timedelta(hours=3))
        if not pending:
            return
        today = now.astimezone(ROME).date()
        resolved = 0
        for sport in {s for _, s in pending}:
            wanted = {k.split(":", 1)[1] for k, s in pending if s == sport}
            try:
                fixtures = self.all.fixtures(sport, today - timedelta(days=3), today)
            except (FeedError, ValueError, OSError) as exc:
                LOG.warning("Risultati %s indisponibili: %s", sport, exc)
                continue
            for f in fixtures:
                ek = str(f.get("event_key", ""))
                if ek in wanted and (winner := final_winner(sport, f)):
                    self.db.store_result(f"{sport}:{ek}", sport, winner, {
                        k: f.get(k) for k in ("event_final_result", "event_ft_result", "event_winner", "event_status")}, now)
                    resolved += 1
        self.db.commit()
        LOG.info("Esiti finali registrati: %d su %d in attesa", resolved, len(pending))

    # --- ciclo ------------------------------------------------------------------------------
    def tick(self, now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        if (now - self.model_loaded).total_seconds() > 3600:
            self.reload_model()
        matches = self.fetch_scores()
        self.archive_scores(matches, now)
        trailing = [m for m in matches if m.behind]
        self.refresh_allsports_odds({f"{m.sport}:{m.event_id}" for m in matches}, now)
        live_markets: dict[str, Market] = {}
        if self.odds is not None:
            try:
                keys = self.odds_keys()
            except (FeedError, ValueError, OSError) as exc:
                LOG.warning("Impossibile ottenere discipline disponibili: %s", exc)
                keys = []
            self.refresh_events(keys, now)
            live_markets = self.fetch_odds(self.odds_plan(keys, trailing, now), now)
        alerts = self.evaluate_all(trailing, live_markets, now)
        self.dispatch(alerts, now)
        self.resolve_results(now)
        self.db.commit()
        today = now.astimezone(ROME).strftime("%Y-%m-%d")
        LOG.info("Ciclo: %d partite live, %d con svantaggio, %d mercati live, %d alert | crediti oggi %d/%d%s",
                 len(matches), len(trailing), len(live_markets), len(alerts), self.db.used_today(today),
                 self.cfg.max_requests_day,
                 f" | residui provider {self.odds.remaining}" if self.odds and self.odds.remaining else "")

    def heartbeat(self):
        try:
            Path(self.cfg.heartbeat_file).write_text(str(int(time.time())), encoding="utf-8")
        except OSError:
            pass

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        LOG.info("Avvio monitor: intervallo %d s, DRY_RUN=%s", self.cfg.poll_seconds, self.cfg.dry_run)
        while not self.stopped:
            started = time.monotonic()
            try:
                self.tick()
                self.heartbeat()
            except Exception:
                LOG.exception("Ciclo interrotto da errore inatteso")
            end = started + self.cfg.poll_seconds
            while not self.stopped and time.monotonic() < end:
                time.sleep(min(1, max(0, end - time.monotonic())))
