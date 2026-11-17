"""Client REST pubblici documentati. Non stampa mai chiavi o URL autenticati."""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class FeedError(RuntimeError):
    pass


def request_json(url: str, *, payload: dict[str, str] | None = None, retries: int = 2,
                 headers_out: dict | None = None):
    """GET/POST JSON con retry esponenziale SOLO su errori di rete e 429/5xx (mai su 401/403/404)."""
    data = urlencode(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, headers={"User-Agent": "OddsIntelligenceLive/0.2", "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=15) as resp:
                if headers_out is not None:
                    headers_out.update({k.lower(): v for k, v in resp.headers.items()})
                return json.loads(resp.read(8_000_000))
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise FeedError(f"HTTP {exc.code}; possibile quota API esaurita o chiave non valida") from None
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            if attempt < retries and not isinstance(exc, ValueError):
                time.sleep(2 ** attempt)
                continue
            raise FeedError(f"Errore risposta rete/API ({type(exc).__name__})") from None
    raise FeedError("Tentativi esauriti")


class AllSports:
    base = "https://apiv2.allsportsapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call(self, sport: str, **params) -> object:
        args = urlencode({**params, "APIkey": self.api_key, "timezone": "Europe/Rome"})
        data = request_json(f"{self.base}/{sport}/?{args}")
        if not isinstance(data, dict) or data.get("success") not in (1, "1", True):
            raise FeedError(f"AllSports {sport}/{params.get('met')}: risposta di errore")
        return data.get("result", [])

    def live(self, sport: str) -> list[dict]:
        result = self._call(sport, met="Livescore")
        if not isinstance(result, list):
            raise FeedError(f"AllSports {sport}: schema Livescore inatteso")
        return [e for e in result if isinstance(e, dict)]

    def odds(self, sport: str, start: date, end: date) -> dict:
        """Quote pre-partita (metodo documentato `Odds`), un'unica chiamata per intervallo di date."""
        result = self._call(sport, met="Odds", **{"from": start.isoformat(), "to": end.isoformat()})
        return result if isinstance(result, dict) else {}

    def fixtures(self, sport: str, start: date, end: date) -> list[dict]:
        result = self._call(sport, met="Fixtures", **{"from": start.isoformat(), "to": end.isoformat()})
        return [e for e in result if isinstance(e, dict)] if isinstance(result, list) else []


class TheOddsAPI:
    base = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, regions: str):
        self.api_key, self.regions = api_key, regions
        self._sports: list[dict] = []
        self._next_refresh = datetime.min.replace(tzinfo=timezone.utc)
        self.remaining: str | None = None   # intestazione x-requests-remaining dell'ultima chiamata

    def sports(self) -> list[dict]:
        """Elenco discipline in stagione: documentato come gratuito (non consuma crediti)."""
        now = datetime.now(timezone.utc)
        if now >= self._next_refresh:
            response = request_json(f"{self.base}/sports/?{urlencode({'apiKey': self.api_key})}")
            if not isinstance(response, list):
                raise FeedError("The Odds API: schema sports inatteso")
            self._sports = [x for x in response if isinstance(x, dict)]
            self._next_refresh = now + timedelta(hours=1)
        return self._sports

    def active_keys(self, preferred: tuple[str, ...], include_tennis: bool = True) -> list[str]:
        by_key = {str(s.get("key")): s for s in self.sports() if s.get("active", True)}
        fixed = [key for key in preferred if key in by_key]
        tennis = [k for k in sorted(by_key) if include_tennis and k.startswith("tennis_") and k not in fixed]
        return fixed + tennis

    def events(self, sport_key: str) -> list[dict]:
        """Calendario eventi (id, commence_time, squadre): documentato come gratuito."""
        data = request_json(f"{self.base}/sports/{quote(sport_key, safe='')}/events/?"
                            f"{urlencode({'apiKey': self.api_key})}")
        if not isinstance(data, list):
            raise FeedError(f"The Odds API: schema events inatteso per {sport_key}")
        return [x for x in data if isinstance(x, dict)]

    def odds_cost(self) -> int:
        """Costo documentato: mercati x regioni (qui 1 mercato h2h)."""
        return max(1, len([r for r in self.regions.split(",") if r.strip()]))

    def odds(self, sport_key: str, event_ids: list[str] | None = None) -> list[dict]:
        params = {"apiKey": self.api_key, "regions": self.regions, "markets": "h2h", "oddsFormat": "decimal"}
        if event_ids:
            params["eventIds"] = ",".join(event_ids)
        headers: dict = {}
        data = request_json(f"{self.base}/sports/{quote(sport_key, safe='')}/odds/?{urlencode(params)}",
                            headers_out=headers)
        self.remaining = headers.get("x-requests-remaining", self.remaining)
        if not isinstance(data, list):
            raise FeedError(f"The Odds API: schema odds inatteso per {sport_key}")
        return [x for x in data if isinstance(x, dict)]


class Telegram:
    def __init__(self, token: str, chat: str):
        self.token, self.chat = token, chat

    def send(self, message: str) -> None:
        result = request_json(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              payload={"chat_id": self.chat, "text": message[:4000],
                                       "disable_web_page_preview": "true"}, retries=0)  # niente retry: eviterebbe doppi invii
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise FeedError("Telegram non ha confermato la consegna")
