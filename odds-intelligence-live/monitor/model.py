"""Modello empirico calibrato: frequenze storiche di rimonta per stato di gioco e forza pre-partita.

Idea: per uno *stato* (es. tennis al meglio dei 3 con favorito sotto 0-1 nei set, oppure calcio
all'intervallo con favorito sotto di un gol) si prendono gli esempi storici con probabilità
pre-partita del favorito vicina a quella osservata (finestra ±bandwidth) e si misura la
frequenza con cui il favorito ha ottenuto l'esito. Si riporta la stima puntuale e un limite
inferiore di Wilson unilaterale: l'alert usa il LIMITE INFERIORE, non la stima puntuale.

Nessun campione sufficiente = nessuna stima (fail closed).
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from itertools import accumulate

OUTCOMES = ("win", "not_lose")
OUTCOME_LABEL = {"win": "vittoria", "not_lose": "almeno pareggio"}


@dataclass(frozen=True)
class Example:
    state: str
    date: str          # ISO yyyy-mm-dd
    pre_prob: float    # probabilità pre-partita senza margine del favorito
    win: int
    not_lose: int
    source: str = ""


@dataclass(frozen=True)
class Estimate:
    point: float
    lower: float
    upper: float
    n: int
    k: int
    bandwidth: float


def wilson(k: int, n: int, z: float) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


class _Index:
    """Esempi di uno stato ordinati per pre_prob, con somme cumulative per query O(log n)."""

    def __init__(self, rows: list[Example]):
        rows = sorted(rows, key=lambda e: e.pre_prob)
        self.keys = [e.pre_prob for e in rows]
        self.cum = {o: [0, *accumulate(getattr(e, o) for e in rows)] for o in OUTCOMES}

    def window(self, p: float, bw: float, outcome: str) -> tuple[int, int]:
        lo, hi = bisect_left(self.keys, p - bw - 1e-12), bisect_right(self.keys, p + bw + 1e-12)
        return hi - lo, self.cum[outcome][hi] - self.cum[outcome][lo]


class EmpiricalModel:
    def __init__(self, examples: list[Example], *, bandwidth: float = 0.05, min_sample: int = 150,
                 z: float = 1.2816):
        self.bandwidth, self.min_sample, self.z = bandwidth, min_sample, z
        by_state: dict[str, list[Example]] = {}
        for e in examples:
            by_state.setdefault(e.state, []).append(e)
        self.index = {s: _Index(rows) for s, rows in by_state.items()}
        self.size = {s: len(rows) for s, rows in by_state.items()}

    def estimate(self, state: str, outcome: str, pre_prob: float) -> Estimate | None:
        idx = self.index.get(state)
        if idx is None or outcome not in OUTCOMES:
            return None
        n, k = idx.window(pre_prob, self.bandwidth, outcome)
        if n < self.min_sample:
            return None
        lower, upper = wilson(k, n, self.z)
        return Estimate(k / n, lower, upper, n, k, self.bandwidth)


@dataclass(frozen=True)
class Validation:
    state: str
    outcome: str
    cutoff: str
    n_test: int
    covered: int            # esempi di test per cui il modello ha dato una stima
    brier: float | None
    logloss: float | None
    alerts: int             # esempi di test che avrebbero generato un alert (limite inferiore > soglia)
    hits: int
    mean_predicted: float | None
    alert_lower: float | None
    passed: bool
    buckets: tuple[tuple[str, int, float, float], ...]   # (fascia, n, predetta media, osservata)
    note: str


def validate(examples: list[Example], cutoff: str, threshold: float, *, bandwidth: float, min_sample: int,
             z: float, min_alerts: int = 30, max_gap: float = 0.05) -> list[Validation]:
    """Validazione fuori tempo: addestra sugli esempi con data < cutoff, verifica su quelli >= cutoff.

    Promosso (passed) solo se, sul periodo di test, gli alert che il modello avrebbe emesso sono
    almeno `min_alerts`, la loro frequenza osservata è STRETTAMENTE > soglia e la probabilità
    media predetta non si discosta da quella osservata di più di `max_gap`.
    """
    train = [e for e in examples if e.date < cutoff]
    test = [e for e in examples if e.date >= cutoff]
    model = EmpiricalModel(train, bandwidth=bandwidth, min_sample=min_sample, z=z)
    results: list[Validation] = []
    states = sorted({e.state for e in examples})
    for state in states:
        outcomes = OUTCOMES if state.startswith("football") else ("win",)
        rows = [e for e in test if e.state == state]
        for outcome in outcomes:
            preds: list[tuple[float, int, float]] = []
            for e in rows:
                est = model.estimate(state, outcome, e.pre_prob)
                if est:
                    preds.append((est.point, getattr(e, outcome), est.lower))
            brier = logloss = mean_pred = alert_lower = None
            if preds:
                brier = sum((p - y) ** 2 for p, y, _ in preds) / len(preds)
                eps = 1e-6
                logloss = -sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
                               for p, y, _ in preds) / len(preds)
            fired = [(p, y) for p, y, lo in preds if lo > threshold]
            hits = sum(y for _, y in fired)
            if fired:
                mean_pred = sum(p for p, _ in fired) / len(fired)
                alert_lower = wilson(hits, len(fired), z)[0]
            buckets = []
            for lo_b in (0.0, 0.5, 0.6, 0.7, 0.8, 0.9):
                hi_b = 1.0001 if lo_b == 0.9 else lo_b + 0.1 if lo_b else 0.5
                sel = [(p, y) for p, y, _ in preds if lo_b <= p < hi_b]
                if sel:
                    buckets.append((f"{lo_b:.0%}-{min(hi_b, 1):.0%}", len(sel),
                                    sum(p for p, _ in sel) / len(sel), sum(y for _, y in sel) / len(sel)))
            passed = False
            if len(fired) < min_alerts:
                note = f"alert simulati insufficienti ({len(fired)} < {min_alerts})"
            elif hits / len(fired) <= threshold:
                note = f"frequenza osservata {hits / len(fired):.1%} non > soglia {threshold:.0%}"
            elif abs(mean_pred - hits / len(fired)) > max_gap:
                note = f"calibrazione scarsa: predetto {mean_pred:.1%} vs osservato {hits / len(fired):.1%}"
            else:
                passed, note = True, "promosso"
            results.append(Validation(state, outcome, cutoff, len(rows), len(preds), brier, logloss, len(fired),
                                      hits, mean_pred, alert_lower, passed, tuple(buckets), note))
    return results
