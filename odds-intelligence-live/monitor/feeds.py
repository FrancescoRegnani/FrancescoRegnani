"""Client REST pubblici documentati. Non stampa mai chiavi o URL autenticati."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


class FeedError(RuntimeError):
    pass


def request_json(url: str, *, payload: dict[str, str] | None = None):
    data = urlencode(payload).encode("utf-8") if payload is not None else None
    req = Request(url, data=data, headers={"User-Agent": "OddsIntelligenceLive/0.1", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                raise FeedError(f"HTTP {resp.status}")
            return json.loads(resp.read(8_000_000))
    except HTTPError as exc:
        raise FeedError(f"HTTP {exc.code}; possibile quota API esaurita o chiave non valida") from None
    except (URLError, TimeoutError, ValueError) as exc:
        raise FeedError(f"Errore risposta rete/API ({type(exc).__name__})") from None


class AllSports:
    base = "https://apiv2.allsportsapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def live(self, sport: str) -> list[dict]:
        args = urlencode({"met": "Livescore", "APIkey": self.api_key, "timezone": "Europe/Rome"})
        data = request_json(f"{self.base}/{sport}/?{args}")
        if data.get("success") not in (1, "1", True):
            raise FeedError(f"AllSports {sport}: risposta di errore")
        result = data.get("result", [])
        if not isinstance(result, list):
            raise FeedError(f"AllSports {sport}: schema Livescore inatteso")
        return [e for e in result if isinstance(e, dict)]


class TheOddsAPI:
    base = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str, regions: str):
        self.api_key, self.regions = api_key, regions
        self._sports: list[dict] = []
        self._next_refresh = datetime.min.replace(tzinfo=timezone.utc)

    def sports(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        if now >= self._next_refresh:
            response = request_json(f"{self.base}/sports/?{urlencode({'apiKey': self.api_key})}")
            if not isinstance(response, list):
                raise FeedError("The Odds API: schema sports inatteso")
            self._sports = [x for x in response if isinstance(x, dict)]
            self._next_refresh = now + timedelta(hours=1)
        return self._sports

    def active_keys(self, preferred: tuple[str, ...], max_auto_tennis: int = 6) -> list[str]:
        available = self.sports()
        by_key = {str(s.get("key")): s for s in available}
        # Priorità ai campionati scelti dall'utente; scopre gli ATP/WTA attivi, se offerti.
        fixed = [key for key in preferred if key in by_key]
        tennis = [k for k in sorted(by_key) if k.startswith("tennis_") and k not in fixed]
        return fixed + tennis[:max_auto_tennis]

    def odds(self, sport_key: str) -> list[dict]:
        params = urlencode({"apiKey": self.api_key, "regions": self.regions,
                            "markets": "h2h", "oddsFormat": "decimal"})
        data = request_json(f"{self.base}/sports/{quote(sport_key, safe='')}/odds/?{params}")
        if not isinstance(data, list):
            raise FeedError(f"The Odds API: schema odds inatteso per {sport_key}")
        return [x for x in data if isinstance(x, dict)]


class Telegram:
    def __init__(self, token: str, chat: str):
        self.token, self.chat = token, chat

    def send(self, message: str) -> None:
        result = request_json(f"https://api.telegram.org/bot{self.token}/sendMessage",
                              payload={"chat_id": self.chat, "text": message,
                                       "disable_web_page_preview": "true"})
        if result.get("ok") is not True:
            raise FeedError("Telegram non ha confermato la consegna")
