from datetime import datetime, timezone

import pytest

from app.collector import attach_poly, finalize, parse_espn_event, parse_poly_event
from app.probability import american_to_decimal, confidence_band, consensus, fair_probs, overround


def test_american_to_decimal():
    assert american_to_decimal('+150') == pytest.approx(2.5)
    assert american_to_decimal('-125') == pytest.approx(1.8)
    assert american_to_decimal(245) == pytest.approx(3.45)
    with pytest.raises(ValueError):
        american_to_decimal('+50')


def test_three_way_fair_probs_sum_to_one():
    p = fair_probs({'1': 2.10, 'X': 3.45, '2': 3.05})
    assert sum(p.values()) == pytest.approx(1)
    assert p['1'] > p['2'] > p['X']
    assert overround({'1': 2.10, 'X': 3.45, '2': 3.05}) > 0


def test_consensus_and_band():
    c = consensus([{'A': 0.6, 'B': 0.4}, {'A': 0.7, 'B': 0.3}])
    assert c['A'] == pytest.approx(0.65)
    with pytest.raises(ValueError):
        consensus([{'A': 0.6, 'B': 0.4}, {'A': 0.5, 'C': 0.5}])
    assert confidence_band(0.85, 2) == 'alta'
    assert confidence_band(0.66, 2) == 'media'
    assert confidence_band(0.52, 2) == 'bassa'
    assert confidence_band(0.50, 3) == 'media'


def _espn(sport_draw=False, state='pre'):
    ml = {'home': {'open': {'odds': '-119'}, 'close': {'odds': '-150'}},
          'away': {'open': {'odds': '+101'}, 'close': {'odds': '+130'}}}
    if sport_draw:
        ml['draw'] = {'open': {'odds': '+250'}, 'close': {'odds': '+245'}}
    return {'id': '1', 'date': '2030-01-01T20:00Z', 'competitions': [{
        'status': {'type': {'state': state}},
        'competitors': [{'homeAway': 'home', 'team': {'displayName': 'Home FC', 'name': 'Home'}},
                        {'homeAway': 'away', 'team': {'displayName': 'Away FC', 'name': 'Away'}}],
        'odds': [None, {'provider': {'name': 'DraftKings'}, 'moneyline': ml, 'overUnder': 2.5,
                        'total': {'over': {'close': {'line': 'o2.5', 'odds': '-110'}},
                                  'under': {'close': {'line': 'u2.5', 'odds': '-110'}}}}]}]}


def test_parse_espn_two_way_with_movement():
    r = parse_espn_event(_espn(), 'basket', 'NBA')
    assert r['outcomes_order'] == ['Home FC', 'Away FC']
    assert r['movement']['outcome'] in ('Home FC', 'Away FC')
    assert abs(r['movement']['pp']) > 4
    assert r['totals']['over'] == pytest.approx(0.5)
    out = finalize(r)
    assert out['pick']['name'] == 'Home FC' and out['movement']['flag'] is True


def test_parse_espn_soccer_has_draw_and_skips_started():
    r = parse_espn_event(_espn(sport_draw=True), 'calcio', 'Serie A')
    assert 'Pareggio' in r['outcomes_order'] and len(r['outcomes_order']) == 3
    assert parse_espn_event(_espn(state='in'), 'calcio', 'Serie A') is None


def _poly(prices=('0.62', '0.38'), spread=0.02, start='2030-01-01 20:00:00+00'):
    return {'id': '9', 'title': 'Paris: A Player vs B Player', 'markets': [{
        'sportsMarketType': 'moneyline', 'outcomes': '["A Player", "B Player"]',
        'outcomePrices': '[%s]' % ','.join(f'"{p}"' for p in prices), 'spread': spread,
        'gameStartTime': start, 'acceptingOrders': True, 'liquidityNum': 1000}]}


def test_parse_poly_filters_illiquid_and_resolved():
    now = datetime(2029, 12, 31, tzinfo=timezone.utc)
    r = parse_poly_event(_poly(), 'tennis', 'ATP', now)
    assert r['league'] == 'ATP · Paris' and r['sources'][0]['probs']['A Player'] == pytest.approx(0.62)
    assert parse_poly_event(_poly(spread=0.5), 'tennis', 'ATP', now) is None
    assert parse_poly_event(_poly(prices=('0.995', '0.005')), 'tennis', 'ATP', now) is None
    assert parse_poly_event(_poly(start='2029-01-01 00:00:00+00'), 'tennis', 'ATP', now) is None


def test_attach_poly_by_short_name():
    r = parse_espn_event(_espn(), 'basket', 'NBA')
    p = parse_poly_event({**_poly(), 'markets': [{**_poly()['markets'][0], 'outcomes': '["Away", "Home"]'}]},
                         'basket', 'NBA', datetime(2029, 12, 31, tzinfo=timezone.utc))
    joined, rest = attach_poly([r], [p])
    assert joined == 1 and rest == []
    assert r['sources'][1]['probs'] == {'Home FC': pytest.approx(0.38), 'Away FC': pytest.approx(0.62)}
