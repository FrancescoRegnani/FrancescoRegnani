"""Betfair Exchange API (ufficiale). Chiave applicazione "delayed": gratuita per uso personale, prezzi in ritardo.

Usata per quote pre-partita e live di tennis (anche Challenger), calcio e basket. Exchange =
margine bassissimo: la probabilità è stimata dal punto medio fra miglior puntata (back) e miglior
bancata (lay), solo se il mercato è liquido e la forbice stretta.

Endpoint e metodi dalla documentazione Betfair: login interattivo via API (identitysso), REST
`listMarketCatalogue` e `listMarketBook`. Giurisdizione italiana: domini .it (da verificare col conto).
Sicurezza conto: dopo un login fallito non si riprova per 30 minuti (troppi tentativi bloccano l'account).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .engine import norm, parse_timestamp
from .feeds import FeedError

LOG = logging.getLogger("odds-monitor")
EVENT_TYPES = {"football": "1", "tennis": "2", "basketball": "7522"}
HOSTS = {"it": ("identitysso.betfair.it", "api.betfair.it"),
         "com": ("identitysso.betfair.com", "api.betfair.com"),
         "es": ("identitysso.betfair.es", "api.betfair.es")}
BOOK_BATCH = 40          # EX_BEST_OFFERS pesa 5: 40 mercati = limite di 200 per richiesta
SESSION_TTL = 3 * 3600   # rinnovo prudente della sessione


@dataclass(frozen=True)
class BfMarket:
    market_id: str
    sport: str
    event: str
    competition: str
    start: datetime
    runners: tuple[tuple[int, str], ...]   # (selectionId, nome)

    @property
    def sides(self) -> dict[str, tuple[int, str]]:
        """first/second = primi due partecipanti nell'ordine Betfair (calcio: casa, ospite); draw = pareggio."""
        out: dict[str, tuple[int, str]] = {}
        players = [r for r in self.runners if norm(r[1]) not in {"the draw", "draw"}]
        draws = [r for r in self.runners if norm(r[1]) in {"the draw", "draw"}]
        if len(players) == 2:
            out["first"], out["second"] = players
        if draws:
            out["draw"] = draws[0]
        return out


def book_probabilities(market: BfMarket, book: dict, *, max_rel_spread: float, min_matched: float
                       ) -> tuple[dict[str, float], dict[str, float]] | None:
    """(probabilità normalizzate, migliori quote 'back') per first/second[/draw], oppure None se il mercato
    è sospeso, chiuso, illiquido o con forbice back/lay troppo larga."""
    if book.get("status") != "OPEN" or float(book.get("totalMatched") or 0) < min_matched:
        return None
    runners = {r.get("selectionId"): r for r in book.get("runners", []) if isinstance(r, dict)}
    sides = market.sides
    expected = {"first", "second", "draw"} if market.sport == "football" else {"first", "second"}
    if set(sides) != expected:
        return None
    raw, backs = {}, {}
    for side, (sel, _) in sides.items():
        r = runners.get(sel)
        if not r or r.get("status") != "ACTIVE":
            return None
        ex = r.get("ex") or {}
        back = (ex.get("availableToBack") or [{}])[0].get("price")
        lay = (ex.get("availableToLay") or [{}])[0].get("price")
        if not (back and lay and back > 1 and lay > 1) or lay / back - 1 > max_rel_spread:
            return None
        raw[side] = (1 / back + 1 / lay) / 2
        backs[side] = float(back)
    total = sum(raw.values())
    if not 0.9 <= total <= 1.1:
        return None
    return {k: v / total for k, v in raw.items()}, backs


class Betfair:
    def __init__(self, app_key: str, username: str, password: str, jurisdiction: str = "it"):
        if jurisdiction not in HOSTS:
            raise ValueError("BETFAIR_JURISDICTION deve essere it, com o es")
        self.app_key, self.username, self.password = app_key, username, password
        self.sso, self.api = HOSTS[jurisdiction]
        self.token: str | None = None
        self.token_at = 0.0
        self.login_blocked_until = 0.0

    def login(self) -> None:
        if time.time() < self.login_blocked_until:
            raise FeedError("Betfair: login in pausa dopo un errore")
        req = Request(f"https://{self.sso}/api/login",
                      data=urlencode({"username": self.username, "password": self.password}).encode(),
                      headers={"X-Application": self.app_key, "Accept": "application/json",
                               "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read(100_000))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            self.login_blocked_until = time.time() + 1800
            raise FeedError(f"Betfair login non riuscito ({type(exc).__name__})") from None
        if data.get("status") != "SUCCESS" or not data.get("token"):
            self.login_blocked_until = time.time() + 1800
            raise FeedError(f"Betfair login rifiutato: {data.get('error') or data.get('status')}")
        self.token, self.token_at = data["token"], time.time()
        LOG.info("Betfair: sessione aperta")

    def _call(self, method: str, params: dict, retry: bool = True):
        if not self.token or time.time() - self.token_at > SESSION_TTL:
            self.login()
        req = Request(f"https://{self.api}/exchange/betting/rest/v1.0/{method}/",
                      data=json.dumps(params).encode(),
                      headers={"X-Application": self.app_key, "X-Authentication": self.token or "",
                               "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read(8_000_000))
        except HTTPError as exc:
            body = exc.read(4000).decode("utf-8", "replace")
            if retry and ("INVALID_SESSION" in body or "NO_SESSION" in body):
                self.token = None
                return self._call(method, params, retry=False)
            code = next((c for c in ("TOO_MUCH_DATA", "INVALID_APP_KEY", "TOO_MANY_REQUESTS", "INVALID_INPUT_DATA")
                         if c in body), f"HTTP {exc.code}")
            raise FeedError(f"Betfair {method}: {code}") from None
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            raise FeedError(f"Betfair {method}: errore di rete ({type(exc).__name__})") from None

    def catalogue(self, sport: str, start: datetime, end: datetime) -> list[BfMarket]:
        data = self._call("listMarketCatalogue", {
            "filter": {"eventTypeIds": [EVENT_TYPES[sport]], "marketTypeCodes": ["MATCH_ODDS"],
                       "marketStartTime": {"from": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                           "to": end.strftime("%Y-%m-%dT%H:%M:%SZ")}},
            "marketProjection": ["EVENT", "COMPETITION", "RUNNER_DESCRIPTION", "MARKET_START_TIME"],
            "sort": "FIRST_TO_START", "maxResults": 1000})
        out = []
        for m in data if isinstance(data, list) else []:
            begin = parse_timestamp(m.get("marketStartTime", ""))
            runners = tuple((r.get("selectionId"), str(r.get("runnerName", ""))) for r in m.get("runners", [])
                            if isinstance(r, dict))
            if begin and m.get("marketId") and runners:
                out.append(BfMarket(str(m["marketId"]), sport, str((m.get("event") or {}).get("name", "")),
                                    str((m.get("competition") or {}).get("name", "")), begin, runners))
        return out

    def books(self, market_ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for i in range(0, len(market_ids), BOOK_BATCH):
            data = self._call("listMarketBook", {"marketIds": market_ids[i:i + BOOK_BATCH],
                                                 "priceProjection": {"priceData": ["EX_BEST_OFFERS"]}})
            for b in data if isinstance(data, list) else []:
                if isinstance(b, dict) and b.get("marketId"):
                    out[str(b["marketId"])] = b
        return out
