import os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.core import Session, Event, Quote, Anomaly, Evidence, init_db, detect

app = FastAPI(title='Odds Intelligence', version='0.1.0', docs_url='/docs')
@app.on_event('startup')
def startup(): init_db()

def auth(authorization: str | None = Header(default=None)):
    secret = os.getenv('API_TOKEN')
    if not secret or authorization != 'Bearer ' + secret: raise HTTPException(401, 'Invalid API token')

class EventIn(BaseModel):
    id: str
    sport: str
    player_a: str
    player_b: str
    starts_at: datetime
    is_demo: bool = False
class SnapshotIn(BaseModel):
    event_id: str
    bookmaker: str
    prices: dict[str,float]
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_demo: bool = False
class EvidenceIn(BaseModel):
    event_id: str
    headline: str
    source_url: str
    published_at: datetime
    category: str
    assessment: str = 'unverified'

@app.get('/health')
def health(): return {'status':'ok','version':'0.1.0'}
@app.post('/events', dependencies=[Depends(auth)])
def create_event(body: EventIn):
    if body.starts_at.tzinfo is None: raise HTTPException(422,'Timezone required')
    if body.is_demo and os.getenv('ALLOW_DEMO','false').lower() != 'true': raise HTTPException(403,'Demo disabled')
    with Session() as db:
        if db.get(Event,body.id): raise HTTPException(409,'Event already exists')
        db.add(Event(**body.model_dump())); db.commit()
    return {'ok':True}
@app.get('/events', dependencies=[Depends(auth)])
def events():
    with Session() as db:
        return [{'id':e.id,'sport':e.sport,'player_a':e.player_a,'player_b':e.player_b,'starts_at':e.starts_at.isoformat(),'is_demo':e.is_demo} for e in db.scalars(select(Event).order_by(Event.starts_at.desc()).limit(100))]
@app.post('/snapshots', dependencies=[Depends(auth)])
def snapshots(body: SnapshotIn):
    if body.observed_at.tzinfo is None: raise HTTPException(422,'Timezone required')
    with Session() as db:
        e=db.get(Event,body.event_id)
        if not e: raise HTTPException(404,'Unknown event')
        if e.is_demo != body.is_demo: raise HTTPException(422,'Demo flag mismatch')
        if set(body.prices) != {e.player_a,e.player_b} or any(p<=1 for p in body.prices.values()): raise HTTPException(422,'Invalid two-way market')
        if body.observed_at > datetime.now(timezone.utc): raise HTTPException(422,'Future observation not allowed')
        for outcome,price in body.prices.items():
            db.add(Quote(event_id=e.id,bookmaker=body.bookmaker,outcome=outcome,price=price,observed_at=body.observed_at,is_demo=e.is_demo))
        db.commit()
        alerts=detect(db,e.id,threshold_pp=float(os.getenv('MIN_PROBABILITY_MOVE_PP','4')),min_bookmakers=int(os.getenv('MIN_BOOKMAKERS','3')))
        return {'saved':2,'new_anomalies':[a.id for a in alerts]}
@app.get('/events/{event_id}/quotes', dependencies=[Depends(auth)])
def quotes(event_id: str):
    with Session() as db:
        return [{'bookmaker':q.bookmaker,'outcome':q.outcome,'price':q.price,'observed_at':q.observed_at.isoformat(),'is_demo':q.is_demo} for q in db.scalars(select(Quote).where(Quote.event_id==event_id).order_by(Quote.observed_at.desc()).limit(500))]
@app.get('/anomalies', dependencies=[Depends(auth)])
def anomalies():
    with Session() as db:
        return [{'id':a.id,'event_id':a.event_id,'outcome':a.outcome,'move_pp':a.move_pp,'bookmakers':a.bookmakers,'status':a.status,'is_demo':a.is_demo,'first_at':a.first_at.isoformat(),'last_at':a.last_at.isoformat()} for a in db.scalars(select(Anomaly).order_by(Anomaly.id.desc()).limit(100))]
@app.post('/evidence', dependencies=[Depends(auth)])
def evidence(body: EvidenceIn):
    if body.published_at.tzinfo is None: raise HTTPException(422,'Timezone required')
    if body.assessment not in ('unverified','documented','plausible'): raise HTTPException(422,'Invalid assessment')
    if not body.source_url.startswith(('https://','http://')): raise HTTPException(422,'Source URL required')
    with Session() as db:
        if not db.get(Event,body.event_id): raise HTTPException(404,'Unknown event')
        db.add(Evidence(**body.model_dump())); db.commit()
    return {'ok':True}
@app.get('/events/{event_id}/analysis', dependencies=[Depends(auth)])
def analysis(event_id: str):
    with Session() as db:
        if not db.get(Event,event_id): raise HTTPException(404,'Unknown event')
        anomalies=db.scalars(select(Anomaly).where(Anomaly.event_id==event_id).order_by(Anomaly.last_at.desc())).all()
        sources=db.scalars(select(Evidence).where(Evidence.event_id==event_id)).all()
        first_move=min((a.first_at for a in anomalies),default=None)
        eligible=[e for e in sources if first_move and e.published_at.replace(tzinfo=timezone.utc)<=first_move.replace(tzinfo=timezone.utc)]
        return {'event_id':event_id,'status':'evidence_available' if eligible else 'cause_undetermined','warning':'Evidence is not proof of causation. No automatic injury or fatigue claims.', 'anomalies':[{'outcome':a.outcome,'move_pp':a.move_pp} for a in anomalies],'pre_move_evidence':[{'headline':e.headline,'source_url':e.source_url,'category':e.category,'assessment':e.assessment,'published_at':e.published_at.isoformat()} for e in eligible]}
