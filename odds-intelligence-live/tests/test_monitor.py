import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from monitor.__main__ import candidates, sport_for_key, trusted_context
from monitor.config import Config
from monitor.engine import Match, estimate, matches_market, name_match, parse_market, parse_match
from monitor.storage import Storage


NOW = datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc)


def price_book(n: int, first: float = 5.5, second: float = 1.18, draw: float | None = None,
               stamp=NOW):
    outcomes = [{"name": "Cezar Cretu", "price": first + n * 0.03},
                {"name": "Laslo Djere", "price": second + n * 0.002}]
    if draw:
        outcomes.append({"name": "Draw", "price": draw + n * 0.01})
    return {"key": f"book{n}", "markets": [{"key": "h2h", "last_update": stamp.isoformat(),
                                              "outcomes": outcomes}]}


def odds_event(books):
    return {"id": "odds-1", "home_team": "Cezar Cretu", "away_team": "Laslo Djere",
            "commence_time": (NOW - timedelta(minutes=35)).isoformat(), "bookmakers": books}


def tennis_record(first_score="7", second_score="5"):
    return {"event_key": "live-1", "event_live": "1", "event_first_player": "C. Cretu",
            "event_second_player": "L. Djere", "event_status": "Set 2", "event_game_result": "2 - 1",
            "scores": [{"score_set": "1", "score_first": first_score, "score_second": second_score}]}


class MonitorTests(unittest.TestCase):
    def test_tennis_set_7_5(self):
        m = parse_match("tennis", tennis_record())
        self.assertIsNotNone(m)
        self.assertEqual(m.behind, "second")

    def test_tennis_tiebreak_7_6(self):
        m = parse_match("tennis", tennis_record("7", "6"))
        self.assertIsNotNone(m)
        self.assertEqual(m.behind, "second")

    def test_incomplete_set_no_candidate(self):
        self.assertIsNone(parse_match("tennis", tennis_record("4", "3")))

    def test_market_needs_three_fresh_books(self):
        self.assertIsNone(parse_market(odds_event([price_book(0), price_book(1)]), "tennis", NOW, 180, 3))
        old = NOW - timedelta(minutes=15)
        self.assertIsNone(parse_market(odds_event([price_book(0, stamp=old),
                                                    price_book(1, stamp=old),
                                                    price_book(2, stamp=old)]), "tennis", NOW, 180, 3))

    def test_strong_favourite_behind_flagged_when_livemarket_strong(self):
        m = parse_match("tennis", tennis_record())
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        self.assertIsNotNone(market)
        self.assertTrue(matches_market(m, market))
        selected = estimate(m, market, {"first": .11, "second": .89},
                            threshold=.70, min_pre=.62, max_spread=.10)
        self.assertEqual(len(selected), 1)
        self.assertGreater(selected[0].estimated, .70)
        self.assertLess(selected[0].estimated, market.prob["second"])

    def test_strict_threshold_and_injury(self):
        m = parse_match("tennis", tennis_record())
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        self.assertEqual(estimate(m, market, {"first": .1, "second": .9}, threshold=.99,
                                  min_pre=.62, max_spread=.10), [])
        self.assertEqual(estimate(m, market, {"first": .1, "second": .9}, threshold=.7,
                                  min_pre=.62, max_spread=.10, context={"injury": "confirmed"}), [])

    def test_no_prematch_no_signal(self):
        m = parse_match("tennis", tennis_record())
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        self.assertEqual(estimate(m, market, None, threshold=.70, min_pre=.62, max_spread=.10), [])

    def test_football_draw_plus_win(self):
        m = Match("football", "match2", "Home", "Away", "League", "0-1", "65", "first", "", "")
        market = parse_market({"id": "odds-2", "home_team": "Home", "away_team": "Away",
                               "commence_time": (NOW - timedelta(hours=1)).isoformat(),
                               "bookmakers": [
                                   {"markets": [{"key": "h2h", "last_update": NOW.isoformat(), "outcomes": [
                                       {"name": "Home", "price": 2.2 + n * .01},
                                       {"name": "Away", "price": 7.1 + n * .03},
                                       {"name": "Draw", "price": 1.8 + n * .01}]}]} for n in range(3)]},
                              "football", NOW, 180, 3)
        self.assertIsNotNone(market)
        signals = estimate(m, market, {"first": .80, "second": .10, "draw": .10},
                           threshold=.7, min_pre=.62, max_spread=.1)
        self.assertTrue(any(s.outcome == "almeno pareggio" for s in signals))
        self.assertFalse(any(s.outcome == "vittoria" for s in signals))

    def test_context_must_be_sourced_fresh(self):
        m = parse_match("tennis", tennis_record())
        with tempfile.TemporaryDirectory() as folder:
            context_file = Path(folder) / "c.json"
            context_file.write_text(json.dumps({"tennis:live-1": {
                "verified_at": NOW.isoformat(), "injury": "clear", "fatigue": "low",
                "sources": ["https://example.org/medical-update"]}}), encoding="utf-8")
            self.assertEqual(trusted_context(str(context_file), m, NOW)["injury"], "clear")
            self.assertEqual(trusted_context(str(context_file), m, NOW + timedelta(days=2)), {})

    def test_duplicate_alert_prevented(self):
        m = parse_match("tennis", tennis_record())
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        with tempfile.TemporaryDirectory() as folder:
            db = Storage(str(Path(folder) / "m.sqlite3"))
            db.store_pre("odds-1", {"first": .11, "second": .89}, NOW - timedelta(hours=1),
                         {"first": 8.2, "second": 1.16})
            cfg = Config.from_env()
            self.assertEqual(len(candidates([m], [market], db, cfg, NOW)), 1)
            db.sent("tennis:live-1", "vittoria", NOW)
            self.assertEqual(candidates([m], [market], db, cfg, NOW), [])

    def test_sport_key(self):
        self.assertEqual(sport_for_key("soccer_epl"), "football")
        self.assertIsNone(sport_for_key("cricket_ipl"))

    def test_tennis_requires_documented_pregame_price_under_1_20(self):
        m = parse_match("tennis", tennis_record())
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        with tempfile.TemporaryDirectory() as folder:
            db = Storage(str(Path(folder) / "m.sqlite3"))
            db.store_pre("odds-1", {"first": .1, "second": .9}, NOW, {"first": 6, "second": 1.21})
            self.assertEqual(candidates([m], [market], db, Config.from_env(), NOW), [])

    def test_surname_collision_rejected(self):
        self.assertFalse(name_match("L. Smith", "J. Smith", True))
        self.assertTrue(name_match("L. Djere", "Laslo Djere", True))

    def test_football_stoppage_minute_parsed(self):
        m = parse_match("football", {"event_key": "s1", "event_live": "1",
                                     "event_home_team": "Home", "event_away_team": "Away",
                                     "event_status": "45+3", "event_final_result": "0-1"})
        self.assertEqual(m.phase, "45+3")

    def test_basketball_deficit_needs_verifiable_score(self):
        m = parse_match("basketball", {"event_key": "b1", "event_live": "1",
                                       "event_home_team": "Boston Celtics", "event_away_team": "Chicago Bulls",
                                       "event_status": "Q3", "event_final_result": "69 - 73"})
        self.assertEqual(m.behind, "first")
        self.assertIsNone(parse_match("basketball", {"event_key": "b1", "event_live": "1",
                                                     "event_home_team": "Boston Celtics", "event_away_team": "Chicago Bulls",
                                                     "event_status": "Q3", "event_final_result": "? - ?"}))


if __name__ == "__main__":
    unittest.main()
