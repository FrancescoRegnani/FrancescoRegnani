"""Multi-sport pre-match collector: tennis (ATP/WTA), NBA, NHL and football.

Real sources, no key required:
- ESPN public scoreboard JSON: DraftKings moneyline (opening and current),
  totals and 1X2 for football. Used for NBA, NHL and football.
- Polymarket Gamma API: prediction-market prices. Used for tennis (ESPN carries
  no tennis odds) and as a second independent source for NBA and NHL.

Output is one JSON document (see `build()`), consumed by the web dashboard.
Every probability is margin-free (normalized). Nothing here is simulated.

Run:  python -m app.collector --out web/data.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from app.probability import american_to_decimal, confidence_band, consensus, fair_probs, normalize, overround

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard'
POLY = 'https://gamma-api.polymarket.com/events'
USER_AGENT = 'odds-intelligence/0.2 (+research prototype)'

ESPN_LEAGUES = [
    # (sport, league label, ESPN path)
    ('basket', 'NBA', 'basketball/nba'),
    ('hockey', 'NHL', 'hockey/nhl'),
    ('calcio', 'Serie A', 'soccer/ita.1'),
    ('calcio', 'Premier League', 'soccer/eng.1'),
    ('calcio', 'LaLiga', 'soccer/esp.1'),
    ('calcio', 'Bundesliga', 'soccer/ger.1'),
    ('calcio', 'Ligue 1', 'soccer/fra.1'),
    ('calcio', 'Champions League', 'soccer/uefa.champions'),
    ('calcio', 'Europa League', 'soccer/uefa.europa'),
    ('calcio', 'Conference League', 'soccer/uefa.europa.conf'),
]
POLY_SERIES = {'atp': '10365', 'wta': '10366', 'nba': '10345', 'nhl': '10346'}
MAX_POLY_SPREAD = float(os.getenv('MAX_POLY_SPREAD', '0.10'))
MIN_POLY_LIQUIDITY = float(os.getenv('MIN_POLY_LIQUIDITY', '500'))
MOVE_PP = float(os.getenv('MIN_PROBABILITY_MOVE_PP', '4'))


def get_json(client: httpx.Client, url: str, params: dict | None = None, attempts: int = 4):
    """GET with exponential backoff on network errors, 429 and 5xx."""
    delay = 2.0
    for i in range(attempts):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError(f'HTTP {r.status_code}', request=r.request, response=r)
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if i == attempts - 1:
                raise
            print(f'retry {url}: {exc}', file=sys.stderr)
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()  # other 4xx: not retryable
        return r.json()


def _key(name: str) -> str:
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def _parse_time(s: str) -> datetime:
    s = s.strip().replace(' ', 'T').replace('Z', '+00:00')
    if s.endswith('+00'):
        s += ':00'
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _ml(side: dict | None, which: str) -> float | None:
    try:
        return american_to_decimal(side[which]['odds'])
    except (KeyError, TypeError, ValueError):
        return None


def parse_espn_event(e: dict, sport: str, league: str) -> dict | None:
    """Turn one ESPN scoreboard event into a normalized record, or None if unusable."""
    comp = (e.get('competitions') or [{}])[0]
    if comp.get('status', e.get('status', {})).get('type', {}).get('state') != 'pre':
        return None
    teams = {c.get('homeAway'): c.get('team', {}) for c in comp.get('competitors', [])}
    if 'home' not in teams or 'away' not in teams:
        return None
    odds = next((o for o in comp.get('odds') or [] if isinstance(o, dict) and isinstance(o.get('moneyline'), dict)), None)
    if not odds:
        return None
    ml = odds['moneyline']
    home, away = teams['home'].get('displayName'), teams['away'].get('displayName')
    sides = {home: ml.get('home'), away: ml.get('away')}
    if sport == 'calcio':
        sides = {home: ml.get('home'), 'Pareggio': ml.get('draw'), away: ml.get('away')}
    close = {k: _ml(v, 'close') for k, v in sides.items()}
    if any(v is None for v in close.values()):
        return None
    opening = {k: _ml(v, 'open') for k, v in sides.items()}
    rec = {
        'id': 'espn:' + str(e.get('id')),
        'sport': sport,
        'league': league,
        'start': _parse_time(e['date']).isoformat(),
        'home': home,
        'away': away,
        'short': {home: teams['home'].get('name') or home, away: teams['away'].get('name') or away},
        'outcomes_order': list(close),
        'book_odds': {k: round(v, 3) for k, v in close.items()},
        'margin_pct': round(overround(close), 2),
        'sources': [{'name': odds.get('provider', {}).get('name', 'Bookmaker'), 'kind': 'bookmaker', 'probs': fair_probs(close)}],
        'movement': None,
        'totals': None,
    }
    if all(v is not None for v in opening.values()):
        before, after = fair_probs(opening), rec['sources'][0]['probs']
        k = max(after, key=lambda o: abs(after[o] - before[o]))
        rec['movement'] = {'outcome': k, 'pp': round((after[k] - before[k]) * 100, 2),
                           'open_odds': round(opening[k], 3), 'close_odds': round(close[k], 3)}
    tot = odds.get('total') or {}
    try:
        over, under = american_to_decimal(tot['over']['close']['odds']), american_to_decimal(tot['under']['close']['odds'])
        p = fair_probs({'over': over, 'under': under})
        line = odds.get('overUnder') or float(re.sub(r'[^0-9.]', '', tot['over']['close']['line']))
        rec['totals'] = {'line': line, 'over': p['over'], 'under': p['under']}
    except (KeyError, TypeError, ValueError):
        pass
    return rec


def parse_poly_event(e: dict, sport: str, league: str, now: datetime) -> dict | None:
    """Polymarket moneyline market -> record. Skips illiquid or already-started markets."""
    m = next((m for m in e.get('markets', []) if m.get('sportsMarketType') == 'moneyline'), None)
    if not m or m.get('closed') or not m.get('acceptingOrders', True):
        return None
    try:
        names = json.loads(m['outcomes'])
        prices = [float(x) for x in json.loads(m['outcomePrices'])]
        start = _parse_time(m.get('gameStartTime') or e.get('startTime'))
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    spread = m.get('spread')
    if len(names) != 2 or start <= now or spread is None or float(spread) > MAX_POLY_SPREAD:
        return None
    if any(p <= 0.01 or p >= 0.99 for p in prices):
        return None
    if float(m.get('liquidityNum') or 0) < MIN_POLY_LIQUIDITY:
        return None
    probs = normalize(dict(zip(names, prices)))
    title = e.get('title', '')
    tournament = title.split(':')[0].strip() if ':' in title else league
    return {
        'id': 'poly:' + str(e.get('id')),
        'sport': sport,
        'league': league if sport != 'tennis' else f'{league} · {tournament}',
        'start': start.isoformat(),
        'home': names[0],
        'away': names[1],
        'outcomes_order': names,
        'book_odds': None,
        'margin_pct': None,
        'sources': [{'name': 'Polymarket', 'kind': 'mercato', 'probs': probs,
                     'liquidity': round(float(m.get('liquidityNum') or 0)), 'volume': round(float(m.get('volumeNum') or m.get('volume') or 0))}],
        'movement': None,
        'totals': None,
    }


def attach_poly(records: list[dict], poly: list[dict]) -> tuple[int, list[dict]]:
    """Add Polymarket probabilities to ESPN records with the same teams and day.

    Returns the number joined and the Polymarket records that matched nothing
    (games DraftKings has not priced yet); those are kept as single-source events.
    """
    index = {}
    for p in poly:
        day = p['start'][:10]
        index[(day, frozenset({_key(p['home']), _key(p['away'])}))] = p
    joined, used = 0, set()
    for r in records:
        if r['sport'] not in ('basket', 'hockey'):
            continue
        short = r['short']
        for delta in (0, -1, 1):
            day = (datetime.fromisoformat(r['start']) + timedelta(days=delta)).date().isoformat()
            p = index.get((day, frozenset({_key(short[r['home']]), _key(short[r['away']])})))
            if p:
                by_key = {_key(n): v for n, v in p['sources'][0]['probs'].items()}
                probs = {n: by_key[_key(short[n])] for n in (r['home'], r['away'])}
                r['sources'].append({**p['sources'][0], 'probs': probs})
                used.add(id(p))
                joined += 1
                break
    return joined, [p for p in poly if id(p) not in used]


def finalize(r: dict) -> dict:
    probs = consensus([s['probs'] for s in r['sources']])
    order = r.pop('outcomes_order')
    r.pop('short', None)
    r['outcomes'] = [{'name': n, 'prob': round(probs[n], 4), 'fair_odds': round(1 / probs[n], 2),
                      'book_odds': (r['book_odds'] or {}).get(n)} for n in order]
    r.pop('book_odds')
    for s in r['sources']:
        s['probs'] = {k: round(v, 4) for k, v in s['probs'].items()}
    best = max(r['outcomes'], key=lambda o: o['prob'])
    spread_pp = None
    if len(r['sources']) > 1:
        spread_pp = round(max(abs(a['probs'][best['name']] - b['probs'][best['name']])
                              for a in r['sources'] for b in r['sources']) * 100, 2)
    r['pick'] = {'name': best['name'], 'prob': best['prob'], 'band': confidence_band(best['prob'], len(order)),
                 'sources': len(r['sources']), 'source_gap_pp': spread_pp}
    if r['movement'] and abs(r['movement']['pp']) < MOVE_PP:
        r['movement']['flag'] = False
    elif r['movement']:
        r['movement']['flag'] = True
    if r['totals']:
        r['totals'] = {k: round(v, 4) if isinstance(v, float) and k != 'line' else v for k, v in r['totals'].items()}
    return r


def build(days: int = 4) -> dict:
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    # ESPN rejects date ranges for some leagues, so query one day at a time.
    days_list = [f'{now + timedelta(days=i):%Y%m%d}' for i in range(days + 1)]
    records, errors = [], []
    with httpx.Client(timeout=25, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for sport, league, path in ESPN_LEAGUES:
            seen = set()
            for day in days_list:
                try:
                    data = get_json(client, ESPN.format(path=path), {'dates': day})
                except Exception as exc:  # one failing league/day must not drop the others
                    errors.append(f'ESPN {league} {day}: {exc}')
                    continue
                for e in data.get('events', []):
                    rec = parse_espn_event(e, sport, league)
                    if rec and rec['id'] not in seen and now < datetime.fromisoformat(rec['start']) <= horizon:
                        seen.add(rec['id'])
                        records.append(rec)
        poly = {}
        for tag, series in POLY_SERIES.items():
            poly[tag] = []
            try:
                for offset in range(0, 1000, 200):
                    page = get_json(client, POLY, {'series_id': series, 'closed': 'false', 'active': 'true',
                                                   'limit': 200, 'offset': offset})
                    for e in page:
                        sport = 'tennis' if tag in ('atp', 'wta') else ('basket' if tag == 'nba' else 'hockey')
                        rec = parse_poly_event(e, sport, tag.upper(), now)
                        if rec and datetime.fromisoformat(rec['start']) <= horizon:
                            poly[tag].append(rec)
                    if len(page) < 200:
                        break
            except Exception as exc:
                errors.append(f'Polymarket {tag.upper()}: {exc}')
    joined, unmatched = attach_poly(records, poly['nba'] + poly['nhl'])
    records += unmatched + poly['atp'] + poly['wta']
    events = sorted((finalize(r) for r in records), key=lambda r: r['start'])
    return {
        'generated_at': now.isoformat(timespec='seconds'),
        'horizon_days': days,
        'move_threshold_pp': MOVE_PP,
        'sources': {
            'espn_draftkings': 'https://site.api.espn.com (quote DraftKings di apertura e attuali)',
            'polymarket': 'https://gamma-api.polymarket.com (prezzi del mercato predittivo)',
        },
        'stats': {'events': len(events), 'nba_nhl_with_polymarket': joined,
                  'by_sport': {s: sum(1 for e in events if e['sport'] == s) for s in ('tennis', 'basket', 'calcio', 'hockey')}},
        'errors': errors,
        'events': events,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='web/data.json')
    ap.add_argument('--days', type=int, default=4)
    args = ap.parse_args(argv)
    doc = build(args.days)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps(doc['stats']), 'errors:', doc['errors'] or 'none')


if __name__ == '__main__':
    main()
