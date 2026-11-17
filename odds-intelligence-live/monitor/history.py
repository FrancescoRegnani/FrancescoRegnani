"""Import di storico etichettato da file CSV LOCALI scaricati manualmente dall'utente.

Nessun download automatico: football-data.co.uk dichiara i dati gratuiti "per uso privato,
non per prodotti commerciali o raccolta automatica"; verificare sempre i termini della fonte.

Formati supportati:
- calcio, stile football-data.co.uk: Date, HomeTeam, AwayTeam, FTHG, FTAG, HTHG, HTAG e una terna
  di quote 1X2 (AvgH/D/A, BbAvH/D/A, PSH/D/A, B365H/D/A o le versioni di chiusura ...C...).
- tennis, stile tennis-data.co.uk (colonne da verificare sul file reale): Date, Winner, Loser,
  "Best of", W1..W5, L1..L5, Comment e una coppia di quote (AvgW/AvgL, PSW/PSL, B365W/B365L).
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .engine import devig, set_completed
from .model import Example

FOOTBALL_ODDS = ("Avg", "BbAv", "PS", "B365", "AvgC", "PSC", "B365C")
TENNIS_ODDS = (("AvgW", "AvgL"), ("PSW", "PSL"), ("B365W", "B365L"))


def parse_date(value: str) -> str | None:
    value = (value or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _float(row: dict, key: str) -> float | None:
    try:
        value = float(str(row.get(key, "")).strip())
    except ValueError:
        return None
    return value if value > 1.0 else None


def _int(row: dict, key: str) -> int | None:
    try:
        return int(float(str(row.get(key, "")).strip()))
    except ValueError:
        return None


def football_state(deficit: int) -> str:
    return f"football:ht:-{min(deficit, 2)}{'+' if deficit >= 2 else ''}"


def tennis_state(tier: str, best_of: int, fav_sets: int, dog_sets: int) -> str:
    return f"tennis:{tier}:bo{best_of}:{fav_sets}-{dog_sets}"


def football_examples(rows, source: str) -> tuple[list[Example], int]:
    """Solo partite in cui il favorito pre-partita era in svantaggio all'intervallo."""
    out, skipped = [], 0
    for row in rows:
        date = parse_date(row.get("Date", ""))
        goals = [_int(row, k) for k in ("FTHG", "FTAG", "HTHG", "HTAG")]
        probs = None
        for prefix in FOOTBALL_ODDS:
            prices = {k: _float(row, f"{prefix}{s}") for k, s in (("H", "H"), ("D", "D"), ("A", "A"))}
            if all(prices.values()):
                probs = devig(prices)  # type: ignore[arg-type]
                if probs:
                    break
        if not date or None in goals or not probs:
            skipped += 1
            continue
        fthg, ftag, hthg, htag = goals  # type: ignore[misc]
        if probs["H"] == probs["A"]:
            continue
        fav_home = probs["H"] > probs["A"]
        fav_ht, dog_ht = (hthg, htag) if fav_home else (htag, hthg)
        fav_ft, dog_ft = (fthg, ftag) if fav_home else (ftag, fthg)
        if fav_ht >= dog_ht:
            continue
        out.append(Example(football_state(dog_ht - fav_ht), date, probs["H" if fav_home else "A"],
                           int(fav_ft > dog_ft), int(fav_ft >= dog_ft), source))
    return out, skipped


def tennis_examples(rows, source: str, tier: str) -> tuple[list[Example], int]:
    """Per ogni partita completata, registra ogni stato di svantaggio a set raggiunto dal favorito."""
    out, skipped = [], 0
    for row in rows:
        date = parse_date(row.get("Date", ""))
        best_of = _int(row, "Best of")
        if not date or best_of not in (3, 5) or str(row.get("Comment", "Completed")).strip() != "Completed":
            skipped += 1
            continue
        pair = None
        for w_key, l_key in TENNIS_ODDS:
            pw, pl = _float(row, w_key), _float(row, l_key)
            if pw and pl:
                pair = devig({"W": pw, "L": pl})
                if pair:
                    break
        if not pair or pair["W"] == pair["L"]:
            skipped += 1
            continue
        fav_is_winner = pair["W"] > pair["L"]
        fav, dog = 0, 0
        seen: set[str] = set()
        ok = True
        for i in range(1, best_of + 1):
            w, lo = _int(row, f"W{i}"), _int(row, f"L{i}")
            if w is None or lo is None:
                break
            if not set_completed(w, lo):
                ok = False
                break
            fav_won_set = (w > lo) == fav_is_winner
            fav, dog = fav + fav_won_set, dog + (not fav_won_set)
            target = best_of // 2 + 1
            if fav == target or dog == target:
                break
            if fav < dog:
                state = tennis_state(tier, best_of, fav, dog)
                if state not in seen:
                    seen.add(state)
                    out.append(Example(state, date, max(pair.values()), int(fav_is_winner),
                                       int(fav_is_winner), source))
        if not ok:
            skipped += 1
    return out, skipped


def read_csv(path: str | Path) -> list[dict]:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    return list(csv.DictReader(text.splitlines()))


def import_file(path: str | Path, sport: str, source: str = "", tier: str = "") -> tuple[list[Example], int]:
    rows = read_csv(path)
    source = source or Path(path).name
    if sport == "football":
        return football_examples(rows, source)
    if sport == "tennis":
        if tier not in {"atp", "wta", "challenger", "itf"}:
            raise ValueError("Per il tennis indica il livello del file: --tier atp|wta|challenger|itf")
        return tennis_examples(rows, source, tier)
    raise ValueError("Storico disponibile solo per football e tennis")
