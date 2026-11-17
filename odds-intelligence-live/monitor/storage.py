"""Persistenza SQLite: quote pre/live, snapshot punteggi, valutazioni (anche in DRY_RUN),
esiti finali, storico etichettato, validazioni del modello, budget API e anti-duplicazione."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .model import Example, Validation

SCHEMA = """
CREATE TABLE IF NOT EXISTS prematch (
  event_id TEXT PRIMARY KEY, prob TEXT NOT NULL, first_seen TEXT NOT NULL,
  prices TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS alerts (
  match_id TEXT PRIMARY KEY, outcome TEXT NOT NULL, sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quota (
  day TEXT NOT NULL, service TEXT NOT NULL, used INTEGER NOT NULL,
  PRIMARY KEY (day, service)
);
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS odds_snapshots (
  id INTEGER PRIMARY KEY, event_id TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL,
  commence_time TEXT, phase TEXT NOT NULL, first TEXT, second TEXT,
  prob TEXT NOT NULL, prices TEXT NOT NULL, books INTEGER, spread REAL
);
CREATE INDEX IF NOT EXISTS odds_snapshots_event ON odds_snapshots(event_id, observed_at);
CREATE TABLE IF NOT EXISTS score_snapshots (
  id INTEGER PRIMARY KEY, match_key TEXT NOT NULL, observed_at TEXT NOT NULL,
  score TEXT NOT NULL, phase TEXT NOT NULL, data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS score_snapshots_match ON score_snapshots(match_key, observed_at);
CREATE TABLE IF NOT EXISTS evaluations (
  match_key TEXT NOT NULL, outcome TEXT NOT NULL, state TEXT NOT NULL,
  sport TEXT NOT NULL, competition TEXT, first TEXT, second TEXT, target_side TEXT NOT NULL,
  first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, score TEXT, phase TEXT,
  pre_prob REAL, pre_price REAL, live_prob REAL, live_price REAL,
  model_point REAL, model_lower REAL, model_n INTEGER,
  decision TEXT NOT NULL, reason TEXT NOT NULL, sent_at TEXT,
  PRIMARY KEY (match_key, outcome, state)
);
CREATE TABLE IF NOT EXISTS results (
  match_key TEXT PRIMARY KEY, sport TEXT NOT NULL, winner TEXT NOT NULL,
  final TEXT NOT NULL, resolved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
  id INTEGER PRIMARY KEY, state TEXT NOT NULL, date TEXT NOT NULL, pre_prob REAL NOT NULL,
  win INTEGER NOT NULL, not_lose INTEGER NOT NULL, source TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS history_state ON history(state);
CREATE TABLE IF NOT EXISTS validations (
  state TEXT NOT NULL, outcome TEXT NOT NULL, run_at TEXT NOT NULL, passed INTEGER NOT NULL,
  data TEXT NOT NULL, PRIMARY KEY (state, outcome)
);
"""


class Storage:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(prematch)")}
        for name, ddl in (("prices", "TEXT NOT NULL DEFAULT '{}'"), ("source", "TEXT NOT NULL DEFAULT ''"),
                          ("last_prob", "TEXT"), ("last_prices", "TEXT"), ("last_seen", "TEXT")):
            if name not in cols:
                self.conn.execute(f"ALTER TABLE prematch ADD COLUMN {name} {ddl}")
        self.conn.commit()

    # --- quote pre-partita -------------------------------------------------------------
    def store_pre(self, event_id: str, probabilities: dict[str, float], now: datetime,
                  prices: dict[str, float] | None = None, source: str = ""):
        """Conserva la PRIMA quota osservata e aggiorna l'ULTIMA osservata prima dell'inizio."""
        p, q = json.dumps(probabilities), json.dumps(prices or {})
        self.conn.execute("""INSERT INTO prematch (event_id, prob, first_seen, prices, source, last_prob, last_prices, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET last_prob=excluded.last_prob, last_prices=excluded.last_prices,
            last_seen=excluded.last_seen""", (event_id, p, now.isoformat(), q, source, p, q, now.isoformat()))
        self.conn.commit()

    def pre(self, event_id: str) -> dict[str, float] | None:
        """Probabilità pre-partita: l'ultima osservata prima dell'inizio (più vicina alla chiusura)."""
        row = self.conn.execute("SELECT COALESCE(last_prob, prob) FROM prematch WHERE event_id=?",
                                (event_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def pre_prices(self, event_id: str) -> dict[str, float]:
        row = self.conn.execute("SELECT COALESCE(last_prices, prices) FROM prematch WHERE event_id=?",
                                (event_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    # --- archivio ---------------------------------------------------------------------
    def snapshot_odds(self, event_id: str, source: str, now: datetime, commence: datetime | None, phase: str,
                      first: str, second: str, prob: dict, prices: dict, books: int, spread: float):
        self.conn.execute("""INSERT INTO odds_snapshots (event_id, source, observed_at, commence_time, phase, first,
            second, prob, prices, books, spread) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                          (event_id, source, now.isoformat(), commence.isoformat() if commence else None, phase,
                           first, second, json.dumps(prob), json.dumps(prices), books, spread))

    def snapshot_score(self, match_key: str, now: datetime, score: str, phase: str, data: dict):
        self.conn.execute("INSERT INTO score_snapshots (match_key, observed_at, score, phase, data) VALUES (?,?,?,?,?)",
                          (match_key, now.isoformat(), score, phase, json.dumps(data, default=str)))

    def record_evaluation(self, ev: dict, now: datetime):
        """Prima osservazione conservata integralmente; dopo si aggiorna solo last_seen e la decisione
        se diventa più forte (shadow -> alert). Così il backtest usa il primo istante utile."""
        cols = ("match_key", "outcome", "state", "sport", "competition", "first", "second", "target_side",
                "score", "phase", "pre_prob", "pre_price", "live_prob", "live_price", "model_point",
                "model_lower", "model_n", "decision", "reason")
        values = [ev.get(c) for c in cols]
        self.conn.execute(f"""INSERT INTO evaluations ({', '.join(cols)}, first_seen, last_seen)
            VALUES ({', '.join('?' * len(cols))}, ?, ?)
            ON CONFLICT(match_key, outcome, state) DO UPDATE SET last_seen=excluded.last_seen""",
                          (*values, now.isoformat(), now.isoformat()))
        if ev.get("decision") == "alert":
            # Passaggio a alert: si registra lo snapshot del momento dell'alert (quello da calibrare).
            sets = ", ".join(f"{c}=?" for c in cols[3:])
            self.conn.execute(f"""UPDATE evaluations SET {sets} WHERE match_key=? AND outcome=? AND state=?
                AND decision != 'alert'""", (*values[3:], ev["match_key"], ev["outcome"], ev["state"]))

    def mark_sent(self, match_key: str, outcome: str, state: str, now: datetime):
        self.conn.execute("UPDATE evaluations SET sent_at=?, decision='alert' WHERE match_key=? AND outcome=? AND state=?",
                          (now.isoformat(), match_key, outcome, state))
        self.sent(match_key, outcome, now)

    def unresolved(self, before: datetime, limit: int = 500) -> list[tuple[str, str]]:
        return self.conn.execute("""SELECT DISTINCT e.match_key, e.sport FROM evaluations e
            LEFT JOIN results r ON r.match_key = e.match_key
            WHERE r.match_key IS NULL AND e.first_seen < ? LIMIT ?""", (before.isoformat(), limit)).fetchall()

    def store_result(self, match_key: str, sport: str, winner: str, final: dict, now: datetime):
        self.conn.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)",
                          (match_key, sport, winner, json.dumps(final), now.isoformat()))

    def resolved_evaluations(self) -> list[dict]:
        cur = self.conn.execute("""SELECT e.*, r.winner FROM evaluations e JOIN results r ON r.match_key=e.match_key
            WHERE r.winner IN ('first','second','draw')""")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    def commit(self):
        self.conn.commit()

    # --- storico e validazione --------------------------------------------------------
    def replace_history(self, source: str, examples: list[Example]):
        self.conn.execute("DELETE FROM history WHERE source=?", (source,))
        self.conn.executemany("INSERT INTO history (state, date, pre_prob, win, not_lose, source) VALUES (?,?,?,?,?,?)",
                              [(e.state, e.date, e.pre_prob, e.win, e.not_lose, source) for e in examples])
        # Nuovi dati invalidano le promozioni precedenti: serve una nuova validazione.
        self.conn.execute("DELETE FROM validations")
        self.conn.commit()

    def history(self) -> list[Example]:
        return [Example(*row) for row in self.conn.execute(
            "SELECT state, date, pre_prob, win, not_lose, source FROM history")]

    def save_validations(self, results: list[Validation], now: datetime):
        self.conn.execute("DELETE FROM validations")
        self.conn.executemany("INSERT INTO validations VALUES (?,?,?,?,?)",
                              [(v.state, v.outcome, now.isoformat(), int(v.passed), json.dumps(asdict(v)))
                               for v in results])
        self.conn.commit()

    def approved(self) -> set[tuple[str, str]]:
        return {(s, o) for s, o in self.conn.execute("SELECT state, outcome FROM validations WHERE passed=1")}

    # --- anti-duplicazione e budget ------------------------------------------------------
    def already_alerted(self, match_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM alerts WHERE match_id=?", (match_id,)).fetchone() is not None

    def sent(self, match_id: str, outcome: str, now: datetime):
        self.conn.execute("INSERT OR IGNORE INTO alerts VALUES (?, ?, ?)", (match_id, outcome, now.isoformat()))
        self.conn.commit()

    def used_today(self, today: str, service: str = "odds") -> int:
        row = self.conn.execute("SELECT used FROM quota WHERE day=? AND service=?", (today, service)).fetchone()
        return row[0] if row else 0

    def available_budget(self, today: str, maximum: int, cost: int = 1, service: str = "odds") -> bool:
        return self.used_today(today, service) + cost <= maximum

    def consume(self, today: str, cost: int = 1, service: str = "odds"):
        self.conn.execute("""INSERT INTO quota VALUES (?, ?, ?)
          ON CONFLICT(day, service) DO UPDATE SET used=used+excluded.used""", (today, service, cost))
        self.conn.commit()

    def set_kv(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_kv(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return row[0] if row else None
