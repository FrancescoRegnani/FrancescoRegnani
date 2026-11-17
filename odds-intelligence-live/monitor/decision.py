"""Decisione d'allerta, *fail closed*.

Un alert parte solo se TUTTE le condizioni sono vere:
1. il favorito pre-partita (prob. senza margine >= MIN_PREMATCH_PROBABILITY; tennis: quota <= 1.20)
   è in svantaggio;
2. lo stato di gioco è coperto dallo storico (tennis: inizio di un set dopo averne perso uno;
   calcio: intervallo); il basket non ha ancora storico => mai alert, solo archivio;
3. il modello empirico ha un campione >= MODEL_MIN_SAMPLE e il LIMITE INFERIORE di confidenza
   della probabilità è strettamente > soglia;
4. lo stato/esito è stato PROMOSSO dalla validazione fuori tempo (comando `validate`);
5. il mercato live (se richiesto) è disponibile, non contraddice il modello di oltre
   MAX_MODEL_MARKET_GAP e, se REQUIRE_VALUE, la quota offerta supera la quota equa del modello;
6. nessun infortunio confermato / alta fatica dal contesto manuale verificato.

Ogni valutazione, anche negativa, viene archiviata con il motivo: serve al backtest.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import Config
from .engine import Match, tennis_best_of, tennis_tier
from .history import football_state, tennis_state
from .model import OUTCOME_LABEL, EmpiricalModel, Estimate


@dataclass(frozen=True)
class Quote:
    """Quote orientate come il livescore: first / second / draw."""
    prob: dict[str, float]
    prices: dict[str, float]
    books: int = 0
    spread: float = 0.0
    source: str = ""


@dataclass(frozen=True)
class Evaluation:
    match: Match
    outcome: str
    state: str
    target: str
    decision: str            # alert | shadow | blocked
    reason: str
    pre_prob: float
    pre_price: float | None
    live_prob: float | None
    live_price: float | None
    estimate: Estimate | None
    pre_source: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        return OUTCOME_LABEL.get(self.outcome, self.outcome)

    def as_row(self) -> dict:
        m = self.match
        return {"match_key": f"{m.sport}:{m.event_id}", "outcome": self.outcome, "state": self.state,
                "sport": m.sport, "competition": m.competition, "first": m.first, "second": m.second,
                "target_side": self.target, "score": m.score, "phase": m.phase, "pre_prob": self.pre_prob,
                "pre_price": self.pre_price, "live_prob": self.live_prob, "live_price": self.live_price,
                "model_point": self.estimate.point if self.estimate else None,
                "model_lower": self.estimate.lower if self.estimate else None,
                "model_n": self.estimate.n if self.estimate else None,
                "decision": self.decision, "reason": self.reason}


def match_state(match: Match, cfg: Config) -> tuple[str, str | None]:
    """(etichetta di stato, motivo di NON copertura o None se lo stato è modellabile)."""
    if match.sport == "tennis":
        tier = tennis_tier(match)
        best_of = tennis_best_of(match)
        sets = match.sets or (0, 0)
        fav, dog = (sets[0], sets[1]) if match.behind == "first" else (sets[1], sets[0])
        state = tennis_state(tier, best_of or 0, fav, dog)
        if best_of is None:
            return state, "formato (3 o 5 set) non deducibile con certezza"
        if tier not in cfg.tennis_model_tiers:
            return state, f"livello '{tier}' non coperto dallo storico abilitato (TENNIS_MODEL_TIERS)"
        if match.games is None:
            return state, "game del set in corso non disponibili"
        g_fav, g_dog = (match.games if match.behind == "first" else match.games[::-1])
        if g_fav + g_dog > cfg.tennis_max_games_into_set or g_dog - g_fav > 1:
            return state, "set in corso già avanzato o sfavorevole: lo storico descrive l'inizio del set"
        return state, None
    if match.sport == "football":
        goals = match.goals or (0, 0)
        deficit = abs(goals[0] - goals[1])
        at_break = match.halftime or (cfg.football_ht_tolerance > 0 and match.minute is not None and
                                      45 <= match.minute <= 45 + cfg.football_ht_tolerance)
        if at_break:
            return football_state(deficit), None
        half = "1h" if (match.minute or 0) < 45 else "2h"
        return f"football:{half}:-{min(deficit, 2)}", "lo storico copre solo lo stato all'intervallo"
    if match.sport == "basketball":
        goals = match.goals or (0, 0)
        deficit = abs(goals[0] - goals[1])
        q = re.search(r"([1-4])", match.phase)
        bucket = "1-5" if deficit <= 5 else "6-10" if deficit <= 10 else "11-15" if deficit <= 15 else "16+"
        return f"basketball:q{q.group(1) if q else '?'}:-{bucket}", "nessuno storico calibrato per il basket"
    return f"{match.sport}:?", "sport non supportato"


def evaluate(match: Match, pre: Quote | None, live: Quote | None, model: EmpiricalModel,
             approved: set[tuple[str, str]], cfg: Config, context: dict | None = None) -> list[Evaluation]:
    if not match.behind or not pre:
        return []
    target = match.behind
    pre_prob = pre.prob.get(target)
    if pre_prob is None or pre_prob < cfg.min_pre_probability:
        return []  # chi è sotto non era il favorito: nulla da valutare né archiviare
    pre_price = pre.prices.get(target)
    state, uncovered = match_state(match, cfg)
    details = context or {}
    outcomes = ("win", "not_lose") if match.sport == "football" else ("win",)
    out: list[Evaluation] = []
    for outcome in outcomes:
        live_prob = live_price = None
        if live:
            live_prob = live.prob.get(target, 0) + (live.prob.get("draw", 0) if outcome == "not_lose" else 0)
            live_price = live.prices.get(target) if outcome == "win" else None
        est = model.estimate(state, outcome, pre_prob) if not uncovered else None
        evidence = [f"Prob. pre-partita senza margine: {pre_prob:.1%} ({pre.source or 'n/d'}, {pre.books} bookmaker)"]
        if est:
            evidence.append(f"Storico: {est.k}/{est.n} rimonte riuscite in situazioni simili "
                            f"(pre ±{est.bandwidth:.0%}), intervallo {est.lower:.1%}–{est.upper:.1%}")
        if live and live_prob is not None:
            evidence.append(f"Mercato live senza margine: {live_prob:.1%} ({live.books} bookmaker, "
                            f"divergenza {live.spread:.1%})")
        evidence.append("Infortuni: " + {"clear": "nessuno (verificato)", "confirmed": "CONFERMATO"}.get(
            details.get("injury", ""), "non verificati"))
        evidence.append("Affaticamento: " + {"low": "basso (verificato)", "high": "ALTO"}.get(
            details.get("fatigue", ""), "non verificato"))
        evidence += [s for s in details.get("sources", []) if isinstance(s, str) and s.startswith("https://")]

        def result(decision: str, reason: str) -> Evaluation:
            return Evaluation(match, outcome, state, target, decision, reason, pre_prob, pre_price, live_prob,
                              live_price, est, pre.source, tuple(evidence))

        if match.sport == "tennis" and not (pre_price and 1 < pre_price <= cfg.max_tennis_prematch_odds):
            out.append(result("shadow", f"quota pre-partita {pre_price or 'n/d'} oltre {cfg.max_tennis_prematch_odds}"))
            continue
        if details.get("injury") == "confirmed" or details.get("fatigue") == "high":
            out.append(result("blocked", "infortunio confermato o alta fatica"))
            continue
        if uncovered:
            out.append(result("shadow", uncovered))
            continue
        if not est:
            out.append(result("shadow", f"campione storico insufficiente (< {cfg.model_min_sample})"))
            continue
        if est.lower <= cfg.threshold:
            out.append(result("shadow", f"limite inferiore {est.lower:.1%} non > {cfg.threshold:.0%}"))
            continue
        if (state, outcome) not in approved:
            out.append(result("shadow", "stato non promosso dalla validazione fuori campione"))
            continue
        if cfg.require_verified_context and not details:
            out.append(result("shadow", "contesto infortuni/fatica non verificato"))
            continue
        if live is None or live_prob is None:
            if cfg.require_live_market:
                out.append(result("shadow", "mercato live non disponibile"))
                continue
        elif live_prob < est.point - cfg.max_model_market_gap:
            out.append(result("shadow", f"mercato live {live_prob:.1%} molto sotto il modello "
                                        f"{est.point:.1%}: possibile informazione nuova"))
            continue
        if cfg.require_value:
            if live_price is None:
                out.append(result("shadow", "quota live per questo esito non disponibile: valore non verificabile"))
                continue
            needed = (1 + cfg.min_edge) / est.point
            if live_price < needed:
                out.append(result("shadow", f"nessun valore: quota {live_price:.2f} < {needed:.2f} richiesta"))
                continue
        out.append(result("alert", "tutte le condizioni soddisfatte"))
    return out
