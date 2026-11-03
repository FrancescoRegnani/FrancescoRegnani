from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, ForeignKey, String, DateTime, Float, Integer, Boolean, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./odds.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    sport: Mapped[str] = mapped_column(String(40))
    player_a: Mapped[str] = mapped_column(String(150))
    player_b: Mapped[str] = mapped_column(String(150))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
class Quote(Base):
    __tablename__ = 'odds_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('events.id'))
    bookmaker: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(150))
    price: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
class Anomaly(Base):
    __tablename__ = 'anomalies'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('events.id'))
    outcome: Mapped[str] = mapped_column(String(150))
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    move_pp: Mapped[float] = mapped_column(Float)
    bookmakers: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default='unexplained')
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
class Evidence(Base):
    __tablename__ = 'news_evidence'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('events.id'))
    headline: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(1000))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    category: Mapped[str] = mapped_column(String(40))
    assessment: Mapped[str] = mapped_column(String(40), default='unverified')

def init_db(): Base.metadata.create_all(engine)

def normalized_probs(prices: dict[str,float]) -> dict[str,float]:
    if len(prices) != 2 or any(v <= 1 for v in prices.values()): raise ValueError('Two valid decimal prices required')
    raw = {k: 1/v for k,v in prices.items()}
    return {k: v/sum(raw.values()) for k,v in raw.items()}

def detect(session, event_id: str, window_minutes: int = 60, threshold_pp: float = 4, min_bookmakers: int = 3):
    event = session.get(Event, event_id)
    if not event: return []
    rows = session.scalars(select(Quote).where(Quote.event_id == event_id).order_by(Quote.observed_at, Quote.id)).all()
    now = datetime.now(timezone.utc)
    # Only pre-match data; snapshots after start cannot trigger alerts.
    rows = [q for q in rows if q.observed_at.replace(tzinfo=timezone.utc) <= event.starts_at.replace(tzinfo=timezone.utc)]
    grouped = {}
    for q in rows:
        grouped.setdefault(q.bookmaker, []).append(q)
    changes = {event.player_a: [], event.player_b: []}
    for bookmaker, quotes in grouped.items():
        timestamps = sorted(set(q.observed_at for q in quotes))
        if len(timestamps) < 2: continue
        last = timestamps[-1]
        prior = [t for t in timestamps[:-1] if (last-t).total_seconds() <= window_minutes*60]
        if not prior: continue
        first = prior[0]
        def pair(at):
            p = {q.outcome: q.price for q in quotes if q.observed_at == at}
            if set(p) != {event.player_a,event.player_b}: return None
            return normalized_probs(p)
        a,b = pair(first),pair(last)
        if not a or not b: continue
        for outcome in changes:
            changes[outcome].append((bookmaker,(b[outcome]-a[outcome])*100,first,last))
    created = []
    for outcome, values in changes.items():
        positive = [v for v in values if v[1] >= threshold_pp]
        negative = [v for v in values if v[1] <= -threshold_pp]
        qualifying = positive if len(positive) >= min_bookmakers else negative
        if len(qualifying) < min_bookmakers: continue
        first_at = min(v[2] for v in qualifying)
        last_at = max(v[3] for v in qualifying)
        # Suppress duplicates for the same event/outcome and most recent observation time.
        existing = session.scalar(select(Anomaly).where(Anomaly.event_id==event_id, Anomaly.outcome==outcome, Anomaly.last_at==last_at))
        if existing: continue
        move = round(sum(v[1] for v in qualifying)/len(qualifying),3)
        item = Anomaly(event_id=event_id,outcome=outcome,first_at=first_at,last_at=last_at,move_pp=move,bookmakers=len(qualifying),is_demo=event.is_demo)
        session.add(item); created.append(item)
    session.commit()
    return created
