"""Pure probability helpers shared by the API and the multi-sport collector.

All functions are side-effect free so they can be unit tested without network
or database access.
"""
from __future__ import annotations


def american_to_decimal(odds: str | int | float) -> float:
    """Convert American odds ("+150", "-125", 245) to decimal odds."""
    value = float(str(odds).replace('+', '').strip())
    if value == 0 or -100 < value < 100:
        raise ValueError(f'Invalid American odds: {odds!r}')
    return 1 + value / 100 if value > 0 else 1 + 100 / abs(value)


def implied(prices: dict[str, float]) -> dict[str, float]:
    """Raw implied probabilities 1/price (they include the bookmaker margin)."""
    if len(prices) < 2 or any(v <= 1 for v in prices.values()):
        raise ValueError('At least two valid decimal prices required')
    return {k: 1 / v for k, v in prices.items()}


def normalize(probs: dict[str, float]) -> dict[str, float]:
    """Scale probabilities so they sum to 1 (removes the overround / vig)."""
    total = sum(probs.values())
    if total <= 0 or any(v < 0 for v in probs.values()):
        raise ValueError('Probabilities must be non-negative with a positive sum')
    return {k: v / total for k, v in probs.items()}


def fair_probs(prices: dict[str, float]) -> dict[str, float]:
    """Margin-free probabilities from decimal prices, for 2-way or 3-way markets."""
    return normalize(implied(prices))


def overround(prices: dict[str, float]) -> float:
    """Bookmaker margin in percent (e.g. 4.5 means the book sums to 104.5%)."""
    return (sum(implied(prices).values()) - 1) * 100


def consensus(sources: list[dict[str, float]]) -> dict[str, float]:
    """Average several normalized probability sets that share the same outcomes."""
    sources = [s for s in sources if s]
    if not sources:
        raise ValueError('No sources')
    keys = set(sources[0])
    if any(set(s) != keys for s in sources):
        raise ValueError('Sources disagree on outcomes')
    return normalize({k: sum(s[k] for s in sources) / len(sources) for k in keys})


def confidence_band(p: float, outcomes: int) -> str:
    """Human label for how clear the favourite is, relative to a coin flip."""
    base = 1 / outcomes
    edge = p - base
    if edge >= 0.30:
        return 'alta'
    if edge >= 0.15:
        return 'media'
    return 'bassa'
