"""Monitor live ogni 60 secondi. Default: modalità osservazione, nessun invio."""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config
from .engine import Match, Market, Signal, estimate, map_outcome, matches_market, parse_market, parse_match
from .feeds import AllSports, FeedError, Telegram, TheOddsAPI
from .storage import Storage

LOG = logging.getLogger("odds-monitor")
ROME = ZoneInfo("Europe/Rome")
SPORTS = ("tennis", "football", "basketball")


def sport_for_key(key: str) -> str | None:
    if key.startswith("tennis_"):
        return "tennis"
    if key.startswith("soccer_"):
        return "football"
    if key.startswith("basketball_"):
        return "basketball"
    return None


def trusted_context(path: str, match: Match, now: datetime) -> dict:
    """Solo attestazioni recenti, con link HTTPS; altrimenti informazioni sconosciute."""
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


def format_alert(signal_: Signal, now: datetime, dry_run: bool) -> str:
    m = signal_.match
    url = "https://the-odds-api.com/"  # URL dei dati, non della singola partita.
    positives = "; ".join(signal_.evidence)
    when = now.astimezone(ROME).strftime("%d/%m/%Y %H:%M:%S %Z")
    pre = f"{signal_.pre_probability:.1%}"
    pre_quote = f"{signal_.pre_quote:.2f}" if signal_.pre_quote else "n/d"
    live_quote = f"{signal_.quote:.2f}" if signal_.quote is not None else "n/d (mercato double chance non acquisito)"
    return (f"{'[SIMULAZIONE] ' if dry_run else ''}POSSIBILE RIMONTA\n"
            f"{m.sport.upper()} | {m.competition or 'Competizione da verificare'}\n"
            f"{m.first} - {m.second}\n"
            f"Punteggio: {m.score} | fase: {m.phase} | ora Italia: {when}\n"
            f"Squadra/giocatore in svantaggio: {m.first if m.behind == 'first' else m.second}\n"
            f"Esito: {signal_.outcome}\n"
            f"Probabilità finale stimata: {signal_.estimated:.1%} (euristica, NON calibrata)\n"
            f"Mercato live senza margine: {signal_.market_probability:.1%}; "
            f"rettifica prudenziale: -{signal_.uncertainty:.1%}\n"
            f"Probabilità da quote pre-partita: {pre}; quota pre osservata: {pre_quote}\n"
            f"Quota live mediana: {live_quote} | quota equa stimata: {signal_.fair_quote:.2f}\n"
            f"Fattori / limiti: {positives}\n"
            f"Fiducia: BASSA fino a backtest/calibrazione e conferma clinica/sportiva.\n"
            f"Provider dei dati (non link alla singola partita): {url} e AllSports (https://allsportsapi.com/)")


def candidates(matches: list[Match], markets: list[Market], storage: Storage, cfg: Config,
               now: datetime) -> list[Signal]:
    found: list[Signal] = []
    for match in matches:
        if storage.already_alerted(f"{match.sport}:{match.event_id}"):
            continue
        related = [market for market in markets if matches_market(match, market)]
        # Nomi ambigui = nessun alert. Un mercato non può appartenere a due eventi live.
        related = [market for market in related if sum(matches_market(other, market) for other in matches) == 1]
        if len(related) != 1:
            continue
        market = related[0]
        pre = storage.pre(market.event_id)
        prematch_prices = storage.pre_prices(market.event_id)
        if match.sport == "tennis":
            # La quota iniziale osservata deve essere <= 1.20, con evidenza pre-gara archiviata.
            target = map_outcome(match, market, match.behind)
            if not (1 < prematch_prices.get(target, float("inf")) <= cfg.max_tennis_prematch_odds):
                continue
        ctx = trusted_context(cfg.context_file, match, now)
        signals = estimate(match, market, pre, threshold=cfg.threshold,
                           min_pre=cfg.min_pre_probability, max_spread=cfg.max_spread, context=ctx)
        if signals:
            # Preferisce vittoria se >70%, altrimenti per il calcio almeno pareggio.
            chosen = next((s for s in signals if s.outcome == "vittoria"), signals[0])
            found.append(replace(chosen, pre_quote=prematch_prices.get(map_outcome(match, market, match.behind))))
    return found


class Monitor:
    def __init__(self, cfg: Config):
        cfg.validate(live=True)
        self.cfg = cfg
        self.db = Storage(cfg.db_path)
        self.all = AllSports(cfg.allsports_key)
        self.odds = TheOddsAPI(cfg.odds_key, cfg.regions)
        self.telegram = Telegram(cfg.telegram_token, cfg.telegram_chat) if not cfg.dry_run else None
        self.stopped = False

    def stop(self, *_):
        self.stopped = True

    def tick(self):
        now = datetime.now(timezone.utc)
        today = now.astimezone(ROME).strftime("%Y-%m-%d")
        matches: list[Match] = []
        markets: list[Market] = []
        try:
            keys = self.odds.active_keys(self.cfg.watch_keys, max_auto_tennis=self.cfg.auto_tennis_limit)
        except FeedError as exc:
            LOG.warning("Impossibile ottenere discipline disponibili: %s", exc)
            keys = []
        jobs = {}
        with ThreadPoolExecutor(max_workers=7) as pool:
            for sport in SPORTS:
                jobs[pool.submit(self.all.live, sport)] = ("score", sport)
            for key in keys:
                if not self.db.available_budget(today, self.cfg.max_requests_day):
                    LOG.warning("Limite richieste quote raggiunto: controlli quote sospesi fino a domani")
                    break
                # Prenota prima di chiamare il provider: evita di superare il budget al riavvio.
                self.db.consume(today)
                jobs[pool.submit(self.odds.odds, key)] = ("odds", key)
            for result in as_completed(jobs):
                kind, name = jobs[result]
                try:
                    records = result.result()
                except (FeedError, ValueError, OSError) as exc:
                    LOG.warning("Feed %s/%s indisponibile: %s", kind, name, exc)
                    continue
                if kind == "score":
                    matches += [parsed for raw in records if (parsed := parse_match(name, raw))]
                else:
                    sport = sport_for_key(name)
                    if not sport:
                        continue
                    for raw in records:
                        # Prepartita: raccoglie prezzi con timestamp fino a 24h, mai dopo lo start.
                        prematch = parse_market(raw, sport, now, 86400, self.cfg.min_books)
                        if prematch and prematch.starts_at > now + timedelta(minutes=2):
                            self.db.store_pre(prematch.event_id, prematch.prob, now, prematch.reference_odds)
                        live = parse_market(raw, sport, now, self.cfg.max_odds_age, self.cfg.min_books)
                        if live and live.starts_at <= now and live.starts_at > now - timedelta(hours=12):
                            markets.append(live)
        signals = candidates(matches, markets, self.db, self.cfg, now)
        LOG.info("Controllati live: %s partite in svantaggio, %s mercati freschi, %s candidati > %.0f%%",
                 len(matches), len(markets), len(signals), self.cfg.threshold * 100)
        for s in signals:
            alert_id = f"{s.match.sport}:{s.match.event_id}"
            message = format_alert(s, now, self.cfg.dry_run)
            if self.cfg.dry_run:
                LOG.info("CANDIDATO, nessun invio:\n%s", message)
            else:
                try:
                    assert self.telegram
                    self.telegram.send(message)
                except (FeedError, ValueError, OSError) as exc:
                    LOG.error("Invio Telegram non riuscito: %s", exc)
                    continue
                self.db.sent(alert_id, s.outcome, now)
                LOG.info("Segnalazione inviata: %s", alert_id)

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        LOG.info("Avvio monitor: intervallo %d s, DRY_RUN=%s", self.cfg.poll_seconds, self.cfg.dry_run)
        while not self.stopped:
            started = time.monotonic()
            try:
                self.tick()
            except Exception:
                # L'errore resta diagnosticabile, il processo rimane disponibile.
                LOG.exception("Ciclo interrotto da errore inatteso")
            remaining = max(0, self.cfg.poll_seconds - (time.monotonic() - started))
            end = time.monotonic() + remaining
            while not self.stopped and time.monotonic() < end:
                time.sleep(min(1, end - time.monotonic()))


def demo():
    """Esempio isolato: dati fittizi, nessuna rete, nessun messaggio Telegram."""
    from tempfile import TemporaryDirectory

    now = datetime.now(timezone.utc)
    record = {"event_live": "1", "event_key": "demo-match", "event_first_player": "C. Cretu",
              "event_second_player": "L. Djere", "event_status": "Set 2",
              "scores": [{"score_first": "7", "score_second": "5", "score_set": "1"}],
              "event_game_result": "2 - 1", "league_name": "Challenger (esempio simulato)"}
    bookmakers = []
    for n in range(4):
        bookmakers.append({"key": f"book{n}", "markets": [{"key": "h2h",
                            "last_update": now.isoformat(), "outcomes": [
                                {"name": "Cezar Cretu", "price": 5.8 + 0.1 * n},
                                {"name": "Laslo Djere", "price": 1.17 + 0.001 * n}]}]})
    market_raw = {"id": "demo-odds", "home_team": "Cezar Cretu", "away_team": "Laslo Djere",
                  "commence_time": (now - timedelta(minutes=50)).isoformat(), "bookmakers": bookmakers}
    match = parse_match("tennis", record)
    market = parse_market(market_raw, "tennis", now, 180, 3)
    assert match and market
    with TemporaryDirectory() as temporary:
        db = Storage(os.path.join(temporary, "demo.sqlite3"))
        db.store_pre(market.event_id, {"first": 0.12, "second": 0.88}, now - timedelta(hours=1),
                     {"first": 6.5, "second": 1.12})
        cfg = Config.from_env()
        picked = candidates([match], [market], db, cfg, now)
        print("DEMO: dataset sintetico, non sono dati reali. Nessuna connessione o notifica.")
        print(format_alert(picked[0], now, True) if picked else "Nessun candidato sopra soglia")


def main():
    parser = argparse.ArgumentParser(description="Odds Intelligence: monitor sport in tempo quasi reale")
    parser.add_argument("command", choices=["run", "demo"], nargs="?", default="run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    if args.command == "demo":
        demo()
    else:
        Monitor(Config.from_env()).run()


if __name__ == "__main__":
    main()
