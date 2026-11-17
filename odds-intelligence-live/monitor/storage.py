"""Persistenza SQLite per quote pre-match, limiti di quota e anti-duplicazione."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path


class Storage:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript("""
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
        """)
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(prematch)")}
        if "prices" not in cols:
            self.conn.execute("ALTER TABLE prematch ADD COLUMN prices TEXT NOT NULL DEFAULT '{}'")
            self.conn.commit()

    def store_pre(self, event_id: str, probabilities: dict[str, float], now: datetime,
                  prices: dict[str, float] | None = None):
        self.conn.execute("INSERT OR IGNORE INTO prematch (event_id, prob, first_seen, prices) VALUES (?, ?, ?, ?)",
                          (event_id, json.dumps(probabilities), now.isoformat(), json.dumps(prices or {})))
        self.conn.commit()

    def pre(self, event_id: str) -> dict[str, float] | None:
        row = self.conn.execute("SELECT prob FROM prematch WHERE event_id=?", (event_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def pre_prices(self, event_id: str) -> dict[str, float]:
        row = self.conn.execute("SELECT prices FROM prematch WHERE event_id=?", (event_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def already_alerted(self, match_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM alerts WHERE match_id=?", (match_id,)).fetchone() is not None

    def sent(self, match_id: str, outcome: str, now: datetime):
        self.conn.execute("INSERT OR IGNORE INTO alerts VALUES (?, ?, ?)",
                          (match_id, outcome, now.isoformat()))
        self.conn.commit()

    def available_budget(self, today: str, maximum: int) -> bool:
        row = self.conn.execute("SELECT used FROM quota WHERE day=? AND service='odds'", (today,)).fetchone()
        return not row or row[0] < maximum

    def consume(self, today: str):
        self.conn.execute("""INSERT INTO quota VALUES (?, 'odds', 1)
          ON CONFLICT(day, service) DO UPDATE SET used=used+1""", (today,))
        self.conn.commit()
