import os
from datetime import datetime,timezone,timedelta
from app.core import init_db, Session, Event, Quote, detect

def main():
    if os.getenv('ALLOW_DEMO','false').lower()!='true': raise RuntimeError('Set ALLOW_DEMO=true explicitly')
    init_db(); now=datetime.now(timezone.utc); event_id='DEMO:MICHELSEN-LEHECKA'
    with Session() as db:
        if db.get(Event,event_id): print('Demo already loaded'); return
        db.add(Event(id=event_id,sport='tennis_demo',player_a='Michelsen',player_b='Lehecka',starts_at=now+timedelta(hours=3),is_demo=True)); db.flush()
        for book in ['demo_book_1','demo_book_2','demo_book_3']:
            for t,pa,pb in [(now-timedelta(minutes=45),2.70,1.49),(now-timedelta(minutes=5),2.27,1.66)]:
                for name,price in [('Michelsen',pa),('Lehecka',pb)]: db.add(Quote(event_id=event_id,bookmaker=book,outcome=name,price=price,observed_at=t,is_demo=True))
        db.commit(); print('Created anomaly IDs:',[a.id for a in detect(db,event_id)])
if __name__=='__main__': main()
