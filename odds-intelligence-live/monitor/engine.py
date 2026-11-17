"""Normalizzazione di punteggi e quote: nessuna stima di probabilità qui.

La stima calibrata vive in `model.py`, la decisione di allerta in `decision.py`.
"""
from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

FOOTBALL_HALFTIME = {"ht", "half time", "halftime", "half-time"}
FINISHED = {"finished", "ft", "after extra time", "aet", "after penalties", "ap", "after over time",
            "after overtime", "cancelled", "postponed", "abandoned", "retired", "walk over", "interrupted"}
GRAND_SLAMS = ("australian open", "roland garros", "french open", "wimbledon", "us open")


@dataclass(frozen=True)
class Match:
    sport: str
    event_id: str
    first: str
    second: str
    competition: str
    score: str
    phase: str
    behind: str | None
    first_id: str
    second_id: str
    # Stato strutturato (facoltativo, per modello e archivio).
    sets: tuple[int, int] | None = None          # tennis: set vinti (first, second)
    games: tuple[int, int] | None = None         # tennis: game nel set in corso
    goals: tuple[int, int] | None = None         # calcio/basket: punteggio
    minute: int | None = None                    # calcio: minuto di gioco
    halftime: bool = False                       # calcio: intervallo
    category: str = ""                           # tennis: es. "Atp Singles", "Challenger Men Singles"


@dataclass(frozen=True)
class Market:
    event_id: str
    sport: str
    first: str
    second: str
    starts_at: datetime
    prob: dict[str, float]
    reference_odds: dict[str, float]
    count: int
    spread: float
    newest: datetime | None = None


def numeric_result(value: Any) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d+)\s*[-:]\s*(\d+)\s*", str(value or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def norm(value: str) -> str:
    raw = unicodedata.normalize("NFKD", str(value).casefold())
    ascii_text = "".join(c for c in raw if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def name_match(left: str, right: str, tennis: bool) -> bool:
    a, b = norm(left).split(), norm(right).split()
    if not a or not b:
        return False
    if tennis:
        # Le abbreviazioni dei tennisti sono comuni nei livescore.
        if len(a) > 1 and len(b) > 1 and a[0] == b[-1] and a[-1] == b[0]:
            return True
        if a[-1] != b[-1]:
            return False
        # Due tennisti con lo stesso cognome e iniziali diverse non coincidono.
        return len(a) == 1 or len(b) == 1 or a[0][0] == b[0][0]
    return a == b or (len(a) >= 2 and len(b) >= 2 and set(a) == set(b))


def set_completed(s1: int, s2: int) -> bool:
    return max(s1, s2) >= 6 and (abs(s1 - s2) >= 2 or sorted((s1, s2)) == [6, 7])


def is_doubles(first: str, second: str) -> bool:
    return "/" in first or "/" in second


def tennis_best_of(match: Match) -> int | None:
    """3 o 5 set; None se non deducibile con certezza (=> nessun alert)."""
    cat, comp = norm(match.category), norm(match.competition)
    if "doubles" in cat:
        return None
    if cat.startswith("wta") or "women" in cat or cat.startswith("challenger") or cat.startswith("itf"):
        return 3
    if cat.startswith("atp"):
        return 5 if any(s in comp for s in GRAND_SLAMS) and "qualif" not in comp else 3
    return None


def tennis_tier(match: Match) -> str:
    cat = norm(match.category)
    for tier in ("atp", "wta", "challenger", "itf"):
        if cat.startswith(tier):
            return tier
    return "unknown"


def parse_match(sport: str, entry: dict[str, Any], require_behind: bool = True) -> Match | None:
    if str(entry.get("event_live", "")) not in {"1", "True", "true"}:
        return None
    if not entry.get("event_key"):
        return None
    phase = str(entry.get("event_status", "")).strip()
    if phase.casefold() in FINISHED:
        return None
    sets = games = goals = None
    minute: int | None = None
    halftime = False
    category = ""
    if sport == "tennis":
        first = str(entry.get("event_first_player", ""))
        second = str(entry.get("event_second_player", ""))
        category = str(entry.get("event_type_type", ""))
        match_set = re.fullmatch(r"Set\s+([1-5])", phase, re.IGNORECASE)
        if not match_set or is_doubles(first, second):
            return None
        current_set = int(match_set.group(1))
        won = [0, 0]
        set_results: list[str] = []
        for item in entry.get("scores", []):
            if not isinstance(item, dict):
                continue
            try:
                idx = int(item.get("score_set", 0))
                s1, s2 = int(float(item["score_first"])), int(float(item["score_second"]))
            except (ValueError, TypeError, KeyError):
                continue
            if idx == current_set:
                games = (s1, s2)
            if idx >= current_set or not set_completed(s1, s2):
                continue
            won[0 if s1 > s2 else 1] += 1
            set_results.append(f"{s1}-{s2}")
        if current_set >= 2 and len(set_results) != current_set - 1:
            # Il feed non espone tutti i set conclusi: non inventare uno svantaggio.
            return None
        sets = (won[0], won[1])
        behind = "first" if won[0] < won[1] else "second" if won[1] < won[0] else None
        if games is None:
            games = numeric_result(entry.get("event_game_result"))
        score = ", ".join(set_results) + f" | set {current_set}: {entry.get('event_game_result', '?')}"
        first_id = str(entry.get("first_player_key", ""))
        second_id = str(entry.get("second_player_key", ""))
    else:
        first, second = str(entry.get("event_home_team", "")), str(entry.get("event_away_team", ""))
        goals = numeric_result(entry.get("event_final_result"))
        if not goals:
            return None
        behind = "first" if goals[0] < goals[1] else "second" if goals[1] < goals[0] else None
        score = f"{goals[0]}-{goals[1]}"
        if sport == "football":
            m = re.fullmatch(r"(\d{1,3})(?:\+(\d{1,2}))?'?", phase)
            halftime = phase.casefold() in FOOTBALL_HALFTIME
            if m:
                minute = int(m.group(1)) + int(m.group(2) or 0)
            elif not halftime and phase not in {"1H", "2H", "ET"}:
                return None
        if sport == "basketball" and phase.casefold() in {"", "not started", "ns", "scheduled"}:
            return None
        first_id, second_id = str(entry.get("home_team_key", "")), str(entry.get("away_team_key", ""))
    if not (first and second):
        return None
    if require_behind and not behind:
        return None
    return Match(sport, str(entry["event_key"]), first, second, str(entry.get("league_name", "")), score, phase,
                 behind, first_id, second_id, sets, games, goals, minute, halftime, category)


def parse_timestamp(value: str) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else None


def devig(prices: dict[str, float]) -> dict[str, float] | None:
    """Probabilità implicite senza margine (normalizzazione proporzionale)."""
    if not prices or any(p <= 1.0 for p in prices.values()):
        return None
    total = sum(1 / v for v in prices.values())
    if not 0.98 <= total <= 1.25:
        return None
    return {k: (1 / v) / total for k, v in prices.items()}


def parse_market(entry: dict[str, Any], sport: str, now: datetime, max_age: int, min_books: int) -> Market | None:
    first, second = str(entry.get("home_team", "")), str(entry.get("away_team", ""))
    started = parse_timestamp(entry.get("commence_time", ""))
    if not (first and second and started and entry.get("id")):
        return None
    all_books: list[tuple[dict[str, float], dict[str, float]]] = []
    stamps: list[datetime] = []
    expected = {"first", "second", "draw"} if sport == "football" else {"first", "second"}
    for bookmaker in entry.get("bookmakers", []):
        if not isinstance(bookmaker, dict):
            continue
        for mk in bookmaker.get("markets", []):
            if not isinstance(mk, dict) or mk.get("key") != "h2h":
                continue
            stamp = parse_timestamp(mk.get("last_update", ""))
            if not stamp or not -30 <= (now - stamp).total_seconds() <= max_age:
                continue
            raw: dict[str, float] = {}
            for o in mk.get("outcomes", []):
                label = str(o.get("name", ""))
                key = ("draw" if norm(label) == "draw" else
                       "first" if name_match(label, first, sport == "tennis") else
                       "second" if name_match(label, second, sport == "tennis") else "")
                try:
                    price = float(o["price"])
                except (ValueError, TypeError, KeyError):
                    continue
                if key and 1.005 <= price <= 2000:
                    raw[key] = price
            if set(raw) != expected:
                continue
            probs = devig(raw)
            if not probs:
                continue
            all_books.append((probs, raw))
            stamps.append(stamp)
            break
    if len(all_books) < min_books:
        return None
    probabilities = {k: statistics.median(b[0][k] for b in all_books) for k in expected}
    spread = max(max(b[0][k] for b in all_books) - min(b[0][k] for b in all_books) for k in expected)
    prices = {k: statistics.median(b[1][k] for b in all_books) for k in expected}
    return Market(str(entry["id"]), sport, first, second, started, probabilities, prices,
                  len(all_books), spread, max(stamps))


def matches_market(match: Match, market: Market) -> bool:
    t = match.sport == "tennis"
    return match.sport == market.sport and (
        (name_match(match.first, market.first, t) and name_match(match.second, market.second, t)) or
        (name_match(match.first, market.second, t) and name_match(match.second, market.first, t))
    )


def map_outcome(match: Match, market_first: str, target: str) -> str:
    """Converte 'first/second' del livescore nella chiave del mercato (che può avere ordine inverso)."""
    target_name = match.first if target == "first" else match.second
    return "first" if name_match(target_name, market_first, match.sport == "tennis") else "second"


def _book_prices(raw: object) -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(raw, dict):
        for book, value in raw.items():
            try:
                price = float(value)
            except (TypeError, ValueError):
                continue
            if 1.005 <= price <= 2000:
                out[str(book)] = price
    return out


def parse_allsports_odds(sport: str, result: Any, min_books: int, max_spread: float
                         ) -> dict[str, tuple[dict[str, float], dict[str, float], int, float]]:
    """Quote pre-partita AllSports (metodo `Odds`), già indicizzate per event_key: nessun abbinamento per nome.

    Formati documentati: calcio = lista di bookmaker con odd_1/odd_x/odd_2; tennis e basket =
    {"Home/Away": {"Home": {bookmaker: quota}, "Away": {...}}}. Restituisce, per evento,
    (probabilità mediane senza margine, quote mediane, n. bookmaker, divergenza) orientate come
    il livescore: first = casa/primo giocatore.
    """
    out: dict[str, tuple[dict[str, float], dict[str, float], int, float]] = {}
    if not isinstance(result, dict):
        return out
    for event_key, payload in result.items():
        books: list[dict[str, float]] = []
        if sport == "football" and isinstance(payload, list):
            for b in payload:
                if not isinstance(b, dict):
                    continue
                try:
                    books.append({"first": float(b["odd_1"]), "draw": float(b["odd_x"]),
                                  "second": float(b["odd_2"])})
                except (KeyError, TypeError, ValueError):
                    continue
        elif sport in {"tennis", "basketball"} and isinstance(payload, dict):
            ha = payload.get("Home/Away")
            if isinstance(ha, dict):
                home, away = _book_prices(ha.get("Home")), _book_prices(ha.get("Away"))
                books = [{"first": home[b], "second": away[b]} for b in home if b in away]
        priced = [(p, b) for b in books if (p := devig(b))]
        if len(priced) < min_books:
            continue
        keys = priced[0][0].keys()
        probs = {k: statistics.median(p[k] for p, _ in priced) for k in keys}
        spread = max(max(p[k] for p, _ in priced) - min(p[k] for p, _ in priced) for k in keys)
        if spread > max_spread:
            continue
        prices = {k: statistics.median(b[k] for _, b in priced) for k in keys}
        out[str(event_key)] = (probs, prices, len(priced), spread)
    return out


def final_winner(sport: str, entry: dict[str, Any]) -> str | None:
    """Esito finale da un record AllSports Fixtures concluso: first/second/draw, None se incerto."""
    if str(entry.get("event_status", "")).casefold() != "finished":
        return None
    if sport == "tennis":
        w = norm(str(entry.get("event_winner") or ""))
        return "first" if w == "first player" else "second" if w == "second player" else None
    # Calcio: risultato dei 90' (event_ft_result) se presente, coerente con lo storico football-data.
    res = numeric_result(entry.get("event_ft_result")) if sport == "football" else None
    res = res or numeric_result(entry.get("event_final_result"))
    if not res:
        return None
    if res[0] == res[1]:
        return "draw" if sport == "football" else None
    return "first" if res[0] > res[1] else "second"
