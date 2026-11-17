"""Normalizzazione punteggi, quote e selezione prudenziale dei candidati."""
from __future__ import annotations

import re
import statistics
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


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
    stale: bool


@dataclass(frozen=True)
class Signal:
    match: Match
    target: str
    outcome: str
    estimated: float
    market_probability: float
    pre_probability: float
    quote: float | None
    fair_quote: float
    bookmakers: int
    uncertainty: float
    evidence: tuple[str, ...]
    pre_quote: float | None = None


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


def parse_match(sport: str, entry: dict[str, Any]) -> Match | None:
    if str(entry.get("event_live", "")) not in {"1", "True"}:
        return None
    if sport == "tennis":
        first = str(entry.get("event_first_player", ""))
        second = str(entry.get("event_second_player", ""))
        phase = str(entry.get("event_status", ""))
        match_set = re.fullmatch(r"Set\s+([1-5])", phase, re.IGNORECASE)
        if not match_set or int(match_set.group(1)) < 2:
            return None
        current_set = int(match_set.group(1))
        won = [0, 0]
        set_results: list[str] = []
        for item in entry.get("scores", []):
            if not isinstance(item, dict):
                continue
            try:
                idx = int(item.get("score_set", 0))
                s1, s2 = int(item["score_first"]), int(item["score_second"])
            except (ValueError, TypeError, KeyError):
                continue
            completed = max(s1, s2) >= 6 and (abs(s1 - s2) >= 2 or sorted((s1, s2)) == [6, 7])
            if idx >= current_set or not completed:
                continue
            won[0 if s1 > s2 else 1] += 1
            set_results.append(f"{s1}-{s2}")
        if not set_results:
            # Se il feed non espone i set conclusi, non inventare uno svantaggio.
            return None
        behind = "first" if won[0] < won[1] else "second" if won[1] < won[0] else None
        score = ", ".join(set_results) + f" | set {current_set}: {entry.get('event_game_result', '?')}"
        first_id = str(entry.get("first_player_key", ""))
        second_id = str(entry.get("second_player_key", ""))
    else:
        first, second = str(entry.get("event_home_team", "")), str(entry.get("event_away_team", ""))
        phase = str(entry.get("event_status", ""))
        if phase.casefold() in {"finished", "ft", "after extra time", "cancelled", "postponed"}:
            return None
        result = numeric_result(entry.get("event_final_result"))
        if not result:
            return None
        behind = "first" if result[0] < result[1] else "second" if result[1] < result[0] else None
        score = f"{result[0]}-{result[1]}"
        if sport == "football" and not (re.fullmatch(r"\d{1,3}(?:\+\d{1,2})?", phase) or phase in {"1H", "2H", "HT", "ET"}):
            return None
        if sport == "basketball" and phase.casefold() in {"", "not started", "ns", "scheduled"}:
            return None
        first_id, second_id = str(entry.get("home_team_key", "")), str(entry.get("away_team_key", ""))
    if not (first and second and behind and entry.get("event_key")):
        return None
    return Match(sport, str(entry["event_key"]), first, second, str(entry.get("league_name", "")), score, phase,
                 behind, first_id, second_id)


def parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def parse_market(entry: dict[str, Any], sport: str, now: datetime, max_age: int, min_books: int) -> Market | None:
    first, second = str(entry.get("home_team", "")), str(entry.get("away_team", ""))
    started = parse_timestamp(entry.get("commence_time", ""))
    if not (first and second and started and entry.get("id")):
        return None
    all_books: list[tuple[dict[str, float], dict[str, float]]] = []
    last_times: list[datetime] = []
    for bookmaker in entry.get("bookmakers", []):
        if not isinstance(bookmaker, dict):
            continue
        for mk in bookmaker.get("markets", []):
            if mk.get("key") != "h2h":
                continue
            stamp = parse_timestamp(mk.get("last_update", ""))
            if not stamp or (now - stamp).total_seconds() > max_age or (now - stamp).total_seconds() < -30:
                continue
            raw: dict[str, float] = {}
            for o in mk.get("outcomes", []):
                label = str(o.get("name", ""))
                key = "draw" if norm(label) == "draw" else "first" if name_match(label, first, sport == "tennis") else "second" if name_match(label, second, sport == "tennis") else ""
                try:
                    price = float(o["price"])
                except (ValueError, TypeError, KeyError):
                    continue
                if key and 1.005 <= price <= 2000:
                    raw[key] = price
            expected = {"first", "second", "draw"} if sport == "football" else {"first", "second"}
            if set(raw) != expected:
                continue
            total = sum(1 / v for v in raw.values())
            if not (0.98 <= total <= 1.25):
                continue
            all_books.append(({key: (1 / price) / total for key, price in raw.items()}, raw))
            last_times.append(stamp)
            break
    if len(all_books) < min_books:
        return None
    probabilities = {k: statistics.median(b[0][k] for b in all_books) for k in all_books[0][0]}
    spread = max(max(b[0][k] for b in all_books) - min(b[0][k] for b in all_books) for k in probabilities)
    prices = {k: statistics.median(b[1][k] for b in all_books) for k in probabilities}
    return Market(str(entry["id"]), sport, first, second, started, probabilities, prices,
                  len(all_books), spread, any((now - t).total_seconds() > max_age for t in last_times))


def matches_market(match: Match, market: Market) -> bool:
    return match.sport == market.sport and (
        (name_match(match.first, market.first, match.sport == "tennis") and name_match(match.second, market.second, match.sport == "tennis")) or
        (name_match(match.first, market.second, match.sport == "tennis") and name_match(match.second, market.first, match.sport == "tennis"))
    )


def map_outcome(match: Match, market: Market, target: str) -> str:
    target_name = match.first if target == "first" else match.second
    return "first" if name_match(target_name, market.first, match.sport == "tennis") else "second"


def estimate(match: Match, market: Market, pre: dict[str, float] | None, *, threshold: float,
             min_pre: float, max_spread: float, context: dict[str, Any] | None = None) -> list[Signal]:
    if not match.behind or not pre or market.stale or market.spread > max_spread:
        return []
    target = map_outcome(match, market, match.behind)
    if pre.get(target, 0) < min_pre:
        return []
    details = context or {}
    if details.get("injury") == "confirmed" or details.get("fatigue") == "high":
        return []
    evidence: list[str] = [f"Forza pre-match dal mercato: {pre[target] * 100:.1f}%",
                           f"Consenso live: {market.count} bookmaker, divergenza {market.spread * 100:.1f} punti"]
    # Lo sconto è una REGOLA PRUDENZIALE, non un intervallo di confidenza né un modello clinico.
    base_haircut = 0.03 + market.spread / 2
    if details.get("injury") != "clear":
        base_haircut += 0.015
        evidence.append("Infortuni non verificabili da feed: penalità prudenziale")
    if details.get("fatigue") != "low":
        base_haircut += 0.015
        evidence.append("Affaticamento non verificabile da feed: penalità prudenziale")
    for source in details.get("sources", []):
        if isinstance(source, str) and source.startswith("https://"):
            evidence.append(source)
    outcomes: list[tuple[str, float, float | None]] = [("vittoria", market.prob[target], market.reference_odds[target])]
    if match.sport == "football" and "draw" in market.prob:
        # E' P(vittoria o pareggio): somma delle probabilità dello stesso mercato 1X2.
        # Non inventare quote live double-chance: sono disponibili solo i tre prezzi 1X2.
        outcomes.append(("almeno pareggio", market.prob[target] + market.prob["draw"], None))
    result: list[Signal] = []
    for outcome, prob, quote in outcomes:
        adjusted = max(0, prob - base_haircut)
        if adjusted <= threshold:
            continue
        result.append(Signal(match, target, outcome, adjusted, prob, pre[target], quote,
                             1 / adjusted, market.count, base_haircut, tuple(evidence)))
    return result
