"""Optional polling adapter. Requires ODDS_API_KEY and API subscription coverage."""
import os
import httpx
from datetime import datetime,timezone
from app.core import Session, Event, Quote, detect

BASE='https://api.the-odds-api.com/v4/sports'
def poll():
    key=os.getenv('ODDS_API_KEY')
    if not key: raise RuntimeError('ODDS_API_KEY missing; no real market feed is active')
    with httpx.Client(timeout=25) as client:
        sports=client.get(BASE,params={'apiKey':key}); sports.raise_for_status()
        for sport in sports.json():
            sk=sport.get('key','')
            if not sk.startswith('tennis_') or not sport.get('active'): continue
            r=client.get(f'{BASE}/{sk}/odds',params={'apiKey':key,'regions':'eu','markets':'h2h','oddsFormat':'decimal','dateFormat':'iso'}); r.raise_for_status()
            with Session() as db:
                for item in r.json():
                    home,away=item.get('home_team'),item.get('away_team')
                    if not home or not away or not item.get('commence_time'): continue
                    event_id='oddsapi:'+item['id']; start=datetime.fromisoformat(item['commence_time'].replace('Z','+00:00'))
                    if start<=datetime.now(timezone.utc): continue
                    if not db.get(Event,event_id): db.add(Event(id=event_id,sport=sk,player_a=home,player_b=away,starts_at=start,is_demo=False)); db.flush()
                    for bookmaker in item.get('bookmakers',[]):
                        for market in bookmaker.get('markets',[]):
                            if market.get('key')!='h2h': continue
                            prices={o['name']:o['price'] for o in market.get('outcomes',[]) if 'name' in o and 'price' in o}
                            if set(prices)!={home,away} or any(p<=1 for p in prices.values()): continue
                            observed=datetime.fromisoformat((market.get('last_update') or bookmaker.get('last_update') or datetime.now(timezone.utc).isoformat()).replace('Z','+00:00'))
                            for outcome,price in prices.items():
                                db.add(Quote(event_id=event_id,bookmaker=bookmaker['key'],outcome=outcome,price=float(price),observed_at=observed,is_demo=False))
                    db.commit()
                    detect(db,event_id,threshold_pp=float(os.getenv('MIN_PROBABILITY_MOVE_PP','4')),min_bookmakers=int(os.getenv('MIN_BOOKMAKERS','3')))
if __name__=='__main__': poll()
