"""Fonte gratuita: endpoint JSON pubblici (non documentati ufficialmente) degli scoreboard ESPN.

Accesso "educato" per non sovraccaricare né farsi bloccare, SENZA tecniche di elusione:
- User-Agent onesto, richieste sequenziali con pausa casuale fra una e l'altra;
- ogni scoreboard al massimo una volta per ciclo, riusato per punteggi e quote;
- campionati senza partite in corso o imminenti consultati solo ogni ESPN_IDLE_REFRESH secondi;
- su 403/429 la fonte viene sospesa per ESPN_BACKOFF secondi (niente insistenza).

Converte i dati nel formato AllSports già gestito da engine.py, così il resto del programma non cambia.
Limiti: niente Challenger/ITF; quote solo pre-partita di un bookmaker (DraftKings) per calcio e basket;
nessuna quota tennis. Endpoint non ufficiali: possono cambiare senza preavviso.
"""
from __future__ import annotations

import json
import logging
import random
import re
import threading
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .feeds import FeedError

LOG = logging.getLogger("odds-monitor")
BASE = "https://site.api.espn.com/apis/site/v2/sports"
PATHS = {"football": "soccer", "basketball": "basketball", "tennis": "tennis"}


def american_to_decimal(value) -> float | None:
    try:
        v = float(str(value).replace("+", ""))
    except (TypeError, ValueError):
        return None
    if v >= 100:
        return round(1 + v / 100, 4)
    if v <= -100:
        return round(1 + 100 / -v, 4)
    return None


def _ml(odds: dict, side: str) -> float | None:
    """Moneyline di un lato: 'close' (ultima pre-partita) se presente, altrimenti 'open'."""
    node = ((odds.get("moneyline") or {}).get(side) or {})
    for key in ("close", "open"):
        price = american_to_decimal((node.get(key) or {}).get("odds"))
        if price:
            return price
    legacy = {"home": "homeTeamOdds", "away": "awayTeamOdds", "draw": "drawOdds"}[side]
    return american_to_decimal((odds.get(legacy) or {}).get("moneyLine"))


def _name(c: dict) -> str:
    return str((c.get("athlete") or {}).get("displayName") or (c.get("team") or {}).get("displayName") or
               (c.get("roster") or {}).get("displayName") or "")


def _score(c: dict) -> int | None:
    try:
        return int(float(c.get("score")))
    except (TypeError, ValueError):
        return None


class ESPNFeed:
    def __init__(self, leagues: dict[str, tuple[str, ...]], *, idle_refresh: int = 900, backoff: int = 1800,
                 pause: tuple[float, float] = (0.6, 1.6)):
        self.leagues = leagues
        self.idle_refresh, self.backoff, self.pause = idle_refresh, backoff, pause
        self.cache: dict[str, tuple[float, dict]] = {}
        self.blocked_until = 0.0
        self._last_request = 0.0
        self._lock = threading.Lock()

    # --- accesso HTTP prudente ---------------------------------------------------------------
    def _get(self, url: str) -> dict:
        with self._lock:   # richieste sempre in fila, mai in parallelo
            return self._get_locked(url)

    def _get_locked(self, url: str) -> dict:
        if time.time() < self.blocked_until:
            raise FeedError("ESPN in pausa dopo un rifiuto del server")
        wait = self._last_request + random.uniform(*self.pause) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        req = Request(url, headers={"User-Agent": "OddsIntelligenceLive/0.3 (uso personale, 1 richiesta/min)",
                                    "Accept": "application/json"})
        try:
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read(8_000_000))
        except HTTPError as exc:
            if exc.code in (403, 429):
                self.blocked_until = time.time() + self.backoff
                LOG.warning("ESPN ha risposto %s: fonte sospesa per %d minuti", exc.code, self.backoff // 60)
            raise FeedError(f"ESPN HTTP {exc.code}") from None
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            raise FeedError(f"ESPN errore di rete ({type(exc).__name__})") from None
        finally:
            self._last_request = time.monotonic()
        if not isinstance(data, dict):
            raise FeedError("ESPN: schema inatteso")
        return data

    def _busy(self, board: dict, now: datetime) -> bool:
        """Partite in corso o in partenza entro 30 minuti: allora serve aggiornare ogni ciclo."""
        for ev in board.get("events", []):
            for comp in self._competitions(ev):
                state = ((comp.get("status") or ev.get("status") or {}).get("type") or {}).get("state")
                if state == "in":
                    return True
                try:
                    start = datetime.fromisoformat(str(comp.get("date") or ev.get("date")).replace("Z", "+00:00"))
                except ValueError:
                    continue
                if state == "pre" and now <= start <= now + timedelta(minutes=30):
                    return True
        return False

    def scoreboard(self, sport: str, league: str, day: date | None = None, max_age: float = 50) -> dict:
        url = f"{BASE}/{PATHS[sport]}/{league}/scoreboard" + (f"?dates={day:%Y%m%d}" if day else "")
        cached = self.cache.get(url)
        now = datetime.now(timezone.utc)
        if cached:
            age = time.time() - cached[0]
            limit = max_age if day or self._busy(cached[1], now) else self.idle_refresh
            if age < limit:
                return cached[1]
        board = self._get(url)
        self.cache[url] = (time.time(), board)
        return board

    @staticmethod
    def _competitions(ev: dict) -> list[dict]:
        if ev.get("groupings"):
            return [c for g in ev["groupings"] for c in g.get("competitions", [])]
        return ev.get("competitions", [])

    # --- conversione in formato AllSports -------------------------------------------------------
    def _convert(self, sport: str, league: str, ev: dict, comp: dict) -> dict | None:
        status = comp.get("status") or ev.get("status") or {}
        stype = status.get("type") or {}
        state, name = stype.get("state"), str(stype.get("name", ""))
        comps = comp.get("competitors") or []
        if len(comps) != 2:
            return None
        rec: dict = {"event_key": f"{league}-{comp.get('id')}", "league_name": str(ev.get("name") or league),
                     "event_live": "1" if state == "in" else "0", "source": "ESPN"}
        if state == "post" and stype.get("completed"):
            rec["event_status"] = "Finished"
        if sport == "tennis":
            ctype = str((comp.get("type") or {}).get("slug", ""))
            if "doubles" in ctype or "mixed" in ctype:
                return None
            first, second = sorted(comps, key=lambda c: c.get("order", 9))
            rec.update({"event_first_player": _name(first), "event_second_player": _name(second),
                        "first_player_key": str(first.get("id", "")), "second_player_key": str(second.get("id", "")),
                        "country_name": f"{league.capitalize()} Singles"})
            sets1, sets2 = first.get("linescores") or [], second.get("linescores") or []
            rec["scores"] = [{"score_set": str(i + 1), "score_first": str(int(a.get("value", 0))),
                              "score_second": str(int(b.get("value", 0)))} for i, (a, b) in enumerate(zip(sets1, sets2))]
            if state == "in":
                period = int(status.get("period") or len(sets1) or 1)
                rec["event_status"] = f"Set {period}"
                cur = rec["scores"][period - 1] if len(rec["scores"]) >= period else None
                rec["event_game_result"] = f"{cur['score_first']} - {cur['score_second']}" if cur else "0 - 0"
            if rec.get("event_status") == "Finished":
                rec["event_winner"] = "First Player" if first.get("winner") else "Second Player" if second.get("winner") else None
            return rec
        home = next((c for c in comps if c.get("homeAway") == "home"), comps[0])
        away = next((c for c in comps if c is not home), comps[1])
        s1, s2 = _score(home), _score(away)
        rec.update({"event_home_team": _name(home), "event_away_team": _name(away),
                    "home_team_key": str((home.get("team") or {}).get("id", "")),
                    "away_team_key": str((away.get("team") or {}).get("id", ""))})
        if s1 is not None and s2 is not None:
            rec["event_final_result"] = f"{s1} - {s2}"
        period = int(status.get("period") or 0)
        if sport == "football":
            if "HALFTIME" in name:
                rec["event_status"] = "Half Time"
            elif state == "in":
                clock = str(status.get("displayClock", "")).replace("'", "").replace(" ", "")
                m = re.match(r"(\d{1,3})(?:\+(\d{1,2}))?$", clock)
                rec["event_status"] = ("ET" if period > 2 else clock if m else "2H" if period == 2 else "1H")
            elif rec.get("event_status") == "Finished":
                if "AET" in name or "PEN" in name or "EXTRA" in name:
                    rec["event_status"] = "After Extra Time"   # esito dei 90' non ricavabile: non risolto
                else:
                    rec["event_ft_result"] = rec.get("event_final_result")
        else:
            if "HALFTIME" in name:
                rec["event_status"] = "Half Time"
            elif state == "in":
                rec["event_status"] = f"Quarter {period}" if 1 <= period <= 4 else "Overtime"
        return rec

    def _records(self, sport: str, day: date | None = None) -> list[tuple[dict, dict, dict]]:
        out = []
        for league in self.leagues.get(sport, ()):
            try:
                board = self.scoreboard(sport, league, day)
            except FeedError as exc:
                LOG.warning("ESPN %s/%s non disponibile: %s", sport, league, exc)
                continue
            for ev in board.get("events", []):
                for comp in self._competitions(ev):
                    rec = self._convert(sport, league, ev, comp)
                    if rec:
                        out.append((rec, ev, comp))
        return out

    # --- interfaccia compatibile con AllSports ------------------------------------------------------
    def live(self, sport: str) -> list[dict]:
        return [rec for rec, _, _ in self._records(sport) if rec["event_live"] == "1"]

    def odds(self, sport: str, start: date, end: date) -> dict:
        """Quote pre-partita dal widget ESPN (un solo bookmaker), solo per partite non iniziate."""
        result: dict = {}
        if sport == "tennis":
            return result
        for rec, ev, comp in self._records(sport):
            if (((comp.get("status") or {}).get("type") or {}).get("state")) != "pre":
                continue
            for o in comp.get("odds") or []:
                book = str((o.get("provider") or {}).get("name", "ESPN"))
                h, a = _ml(o, "home"), _ml(o, "away")
                if not (h and a):
                    continue
                if sport == "football":
                    d = _ml(o, "draw")
                    if d:
                        result[rec["event_key"]] = [{"odd_bookmakers": book, "odd_1": h, "odd_x": d, "odd_2": a}]
                else:
                    result[rec["event_key"]] = {"Home/Away": {"Home": {book: h}, "Away": {book: a}}}
                break
        return result

    def fixtures(self, sport: str, start: date, end: date) -> list[dict]:
        out: list[dict] = []
        day = start
        while day <= end:
            out += [rec for rec, _, _ in self._records(sport, day) if rec.get("event_status") in
                    ("Finished", "After Extra Time")]
            day += timedelta(days=1)
        return out
