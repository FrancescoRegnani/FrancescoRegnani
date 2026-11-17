import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from monitor.app import Monitor, sport_for_key, trusted_context
from monitor.config import Config
from monitor.decision import Quote, evaluate, match_state
from monitor.engine import (devig, final_winner, matches_market, name_match, parse_allsports_odds, parse_market,
                            parse_match, tennis_best_of)
from monitor.history import football_examples, tennis_examples
from monitor.model import EmpiricalModel, Example, validate, wilson
from monitor.storage import Storage

NOW = datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc)
STATE = "tennis:atp:bo3:0-1"


def cfg(**kw) -> Config:
    base = Config.from_env()
    return replace(base, **{"dry_run": True, "db_path": ":memory:", "context_file": "/nonexistent.json", **kw})


def price_book(n: int, first: float = 3.4, second: float = 1.33, draw: float | None = None, stamp=NOW):
    outcomes = [{"name": "Cezar Cretu", "price": first + n * 0.03},
                {"name": "Laslo Djere", "price": second + n * 0.002}]
    if draw:
        outcomes.append({"name": "Draw", "price": draw + n * 0.01})
    return {"key": f"book{n}", "markets": [{"key": "h2h", "last_update": stamp.isoformat(), "outcomes": outcomes}]}


def odds_event(books, start=NOW - timedelta(minutes=35)):
    return {"id": "odds-1", "home_team": "Cezar Cretu", "away_team": "Laslo Djere",
            "commence_time": start.isoformat(), "bookmakers": books}


def tennis_record(first_score="7", second_score="5", games=("1", "1"), category="Atp Singles", status="Set 2"):
    return {"event_key": "live-1", "event_live": "1", "event_first_player": "C. Cretu",
            "event_second_player": "L. Djere", "event_status": status, "event_game_result": f"{games[0]} - {games[1]}",
            "event_type_type": category, "league_name": "ATP Vienna",
            "scores": [{"score_set": "1", "score_first": first_score, "score_second": second_score},
                       {"score_set": "2", "score_first": games[0], "score_second": games[1]}]}


def synthetic_history(rate=lambda p: 0.25 + 0.65 * p, n=6000, state=STATE):
    import random
    rng = random.Random(1)
    out = []
    for i in range(n):
        p = rng.uniform(0.62, 0.95)
        y = int(rng.random() < rate(p))
        out.append(Example(state, (datetime(2020, 1, 1) + timedelta(days=i // 3)).date().isoformat(), p, y, y))
    return out


PRE = Quote({"first": 0.12, "second": 0.88}, {"first": 7.0, "second": 1.12}, 5, 0.02, "test")
LIVE = Quote({"first": 0.27, "second": 0.73}, {"first": 3.5, "second": 1.33}, 4, 0.02, "test")


class ParsingTests(unittest.TestCase):
    def test_tennis_sets_and_games(self):
        m = parse_match("tennis", tennis_record())
        self.assertEqual((m.behind, m.sets, m.games), ("second", (1, 0), (1, 1)))
        self.assertEqual(parse_match("tennis", tennis_record("7", "6")).behind, "second")

    def test_incomplete_set_no_deficit(self):
        self.assertIsNone(parse_match("tennis", tennis_record("4", "3")))

    def test_doubles_rejected(self):
        rec = tennis_record()
        rec["event_first_player"] = "A. B / C. D"
        self.assertIsNone(parse_match("tennis", rec))

    def test_best_of(self):
        m = parse_match("tennis", tennis_record())
        self.assertEqual(tennis_best_of(m), 3)
        self.assertEqual(tennis_best_of(replace(m, competition="ATP Wimbledon")), 5)
        self.assertEqual(tennis_best_of(replace(m, category="Wta Singles", competition="WTA Wimbledon")), 3)
        self.assertIsNone(tennis_best_of(replace(m, category="")))

    def test_market_needs_three_fresh_books(self):
        self.assertIsNone(parse_market(odds_event([price_book(0), price_book(1)]), "tennis", NOW, 180, 3))
        old = NOW - timedelta(minutes=15)
        self.assertIsNone(parse_market(odds_event([price_book(n, stamp=old) for n in range(3)]), "tennis", NOW, 180, 3))
        market = parse_market(odds_event([price_book(n) for n in range(4)]), "tennis", NOW, 180, 3)
        self.assertEqual(market.count, 4)
        self.assertTrue(matches_market(parse_match("tennis", tennis_record()), market))

    def test_surname_collision_rejected(self):
        self.assertFalse(name_match("L. Smith", "J. Smith", True))
        self.assertTrue(name_match("L. Djere", "Laslo Djere", True))

    def test_football_minute_and_halftime(self):
        base = {"event_key": "s1", "event_live": "1", "event_home_team": "Home", "event_away_team": "Away",
                "event_final_result": "0 - 1"}
        self.assertEqual(parse_match("football", {**base, "event_status": "45+3"}).minute, 48)
        self.assertTrue(parse_match("football", {**base, "event_status": "Half Time"}).halftime)
        self.assertIsNone(parse_match("football", {**base, "event_status": "Finished"}))

    def test_basketball_deficit_needs_verifiable_score(self):
        rec = {"event_key": "b1", "event_live": "1", "event_home_team": "Boston", "event_away_team": "Chicago",
               "event_status": "Quarter 3", "event_final_result": "69 - 73"}
        self.assertEqual(parse_match("basketball", rec).behind, "first")
        self.assertIsNone(parse_match("basketball", {**rec, "event_final_result": "? - ?"}))

    def test_devig(self):
        p = devig({"a": 1.9, "b": 1.9})
        self.assertAlmostEqual(p["a"], 0.5)
        self.assertIsNone(devig({"a": 1.0, "b": 3}))

    def test_allsports_odds_formats(self):
        tennis = {"77": {"Home/Away": {"Home": {"b1": "1.15", "b2": "1.16", "b3": "1.14"},
                                       "Away": {"b1": "5.5", "b2": "5.2", "b3": "5.8"}}}}
        parsed = parse_allsports_odds("tennis", tennis, 3, 0.1)
        self.assertGreater(parsed["77"][0]["first"], 0.8)
        self.assertEqual(parsed["77"][2], 3)
        football = {"9": [{"odd_bookmakers": f"b{i}", "odd_1": "1.5", "odd_x": "4.0", "odd_2": "6.5"} for i in range(3)]}
        self.assertIn("draw", parse_allsports_odds("football", football, 3, 0.1)["9"][0])
        self.assertEqual(parse_allsports_odds("football", football, 4, 0.1), {})

    def test_final_winner(self):
        self.assertEqual(final_winner("tennis", {"event_status": "Finished", "event_winner": "Second Player"}), "second")
        self.assertEqual(final_winner("football", {"event_status": "Finished", "event_ft_result": "1 - 1",
                                                   "event_final_result": "2 - 1"}), "draw")
        self.assertIsNone(final_winner("tennis", {"event_status": "Set 3", "event_winner": None}))

    def test_sport_key(self):
        self.assertEqual(sport_for_key("soccer_epl"), "football")
        self.assertIsNone(sport_for_key("cricket_ipl"))


class HistoryAndModelTests(unittest.TestCase):
    def test_football_history_only_favourite_behind_at_ht(self):
        rows = [{"Date": "12/08/23", "HomeTeam": "A", "AwayTeam": "B", "FTHG": "2", "FTAG": "1", "HTHG": "0",
                 "HTAG": "1", "AvgH": "1.40", "AvgD": "4.8", "AvgA": "8.0"},
                {"Date": "12/08/23", "HomeTeam": "C", "AwayTeam": "D", "FTHG": "1", "FTAG": "1", "HTHG": "1",
                 "HTAG": "0", "AvgH": "1.40", "AvgD": "4.8", "AvgA": "8.0"}]
        ex, skipped = football_examples(rows, "t")
        self.assertEqual(len(ex), 1)
        self.assertEqual((ex[0].state, ex[0].win, ex[0].not_lose, ex[0].date), ("football:ht:-1", 1, 1, "2023-08-12"))

    def test_tennis_history_states(self):
        row = {"Date": "2024-01-10", "Best of": "3", "Comment": "Completed", "W1": "5", "L1": "7", "W2": "6", "L2": "3",
               "W3": "6", "L3": "4", "AvgW": "1.15", "AvgL": "5.5"}
        ex, _ = tennis_examples([row], "t", "atp")
        self.assertEqual([(e.state, e.win) for e in ex], [(STATE, 1)])
        # Favorito sconfitto che non è mai stato sotto nei set prima della fine: nessuno stato di svantaggio.
        upset = {**row, "AvgW": "5.5", "AvgL": "1.15"}
        self.assertEqual(tennis_examples([upset], "t", "atp")[0], [])
        retired = {**row, "Comment": "Retired"}
        self.assertEqual(tennis_examples([retired], "t", "atp"), ([], 1))

    def test_model_fail_closed_on_small_sample(self):
        model = EmpiricalModel(synthetic_history(n=100), min_sample=150)
        self.assertIsNone(model.estimate(STATE, "win", 0.88))
        self.assertIsNone(model.estimate("tennis:atp:bo3:0-2", "win", 0.88))

    def test_model_estimate_and_wilson(self):
        est = EmpiricalModel(synthetic_history()).estimate(STATE, "win", 0.88)
        self.assertLess(est.lower, est.point)
        self.assertAlmostEqual(est.point, 0.25 + 0.65 * 0.88, delta=0.04)
        lo, hi = wilson(70, 100, 1.96)
        self.assertTrue(lo < 0.7 < hi)

    def test_validation_promotes_only_calibrated_states(self):
        good = validate(synthetic_history(), "2024-01-01", 0.70, bandwidth=0.05, min_sample=150, z=1.2816)
        self.assertTrue(good[0].passed)
        # Lo stesso modello applicato a un periodo in cui le rimonte sono crollate non viene promosso.
        drift = [e if e.date < "2024-01-01" else replace(e, win=0, not_lose=0) for e in synthetic_history()]
        bad = validate(drift, "2024-01-01", 0.70, bandwidth=0.05, min_sample=150, z=1.2816)
        self.assertFalse(bad[0].passed)


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.match = parse_match("tennis", tennis_record())
        self.model = EmpiricalModel(synthetic_history())
        self.approved = {(STATE, "win")}

    def decide(self, **kw):
        args = dict(pre=PRE, live=LIVE, model=self.model, approved=self.approved, cfg=cfg(), context=None)
        args.update(kw)
        evs = evaluate(self.match, args["pre"], args["live"], args["model"], args["approved"], args["cfg"],
                       args["context"])
        return evs[0] if evs else None

    def test_alert_when_every_condition_holds(self):
        ev = self.decide()
        self.assertEqual(ev.decision, "alert", ev.reason)
        self.assertGreater(ev.estimate.lower, 0.70)
        self.assertGreaterEqual(ev.live_price * ev.estimate.point, 1.02)

    def test_not_favourite_not_evaluated(self):
        self.assertIsNone(self.decide(pre=Quote({"first": 0.6, "second": 0.4}, {"first": 1.6, "second": 2.4})))
        self.assertIsNone(self.decide(pre=None))

    def test_tennis_prematch_price_limit(self):
        pre = Quote({"first": 0.2, "second": 0.8}, {"first": 4.5, "second": 1.21})
        self.assertIn("quota pre-partita", self.decide(pre=pre).reason)

    def test_requires_validation(self):
        self.assertEqual(self.decide(approved=set()).decision, "shadow")

    def test_strict_threshold_on_lower_bound(self):
        self.assertEqual(self.decide(cfg=cfg(threshold=0.95)).decision, "shadow")

    def test_injury_blocks(self):
        self.assertEqual(self.decide(context={"injury": "confirmed"}).decision, "blocked")

    def test_live_market_required_and_consistent(self):
        self.assertIn("mercato live non disponibile", self.decide(live=None).reason)
        crash = Quote({"first": 0.5, "second": 0.5}, {"first": 1.9, "second": 1.9}, 4, 0.02)
        self.assertIn("molto sotto il modello", self.decide(live=crash).reason)

    def test_no_value_no_alert(self):
        cheap = Quote({"first": 0.2, "second": 0.8}, {"first": 4.6, "second": 1.20}, 4, 0.02)
        self.assertIn("nessun valore", self.decide(live=cheap).reason)
        self.assertEqual(self.decide(live=cheap, cfg=cfg(require_value=False)).decision, "alert")

    def test_set_too_advanced(self):
        self.match = parse_match("tennis", tennis_record(games=("1", "4")))
        self.assertIn("set in corso", self.decide().reason)

    def test_challenger_not_covered_by_default(self):
        self.match = parse_match("tennis", tennis_record(category="Challenger Men Singles"))
        self.assertIn("challenger", self.decide().reason)

    def test_football_states(self):
        base = {"event_key": "f1", "event_live": "1", "event_home_team": "Home", "event_away_team": "Away",
                "event_final_result": "0 - 1"}
        ht = parse_match("football", {**base, "event_status": "Half Time"})
        mid = parse_match("football", {**base, "event_status": "70"})
        self.assertEqual(match_state(ht, cfg()), ("football:ht:-1", None))
        self.assertIsNotNone(match_state(mid, cfg())[1])
        hist = [replace(e, state="football:ht:-1", win=0, not_lose=e.win) for e in synthetic_history()]
        model = EmpiricalModel(hist)
        pre = Quote({"first": 0.88, "second": 0.04, "draw": 0.08}, {"first": 1.12, "second": 20, "draw": 9})
        live = Quote({"first": 0.40, "second": 0.25, "draw": 0.35}, {"first": 2.4, "second": 3.8, "draw": 2.7}, 4, .02)
        evs = {e.outcome: e for e in evaluate(ht, pre, live, model, {("football:ht:-1", "not_lose")}, cfg())}
        self.assertEqual(set(evs), {"win", "not_lose"})
        self.assertEqual(evs["win"].decision, "shadow")
        self.assertIn("valore non verificabile", evs["not_lose"].reason)
        evs = {e.outcome: e for e in evaluate(ht, pre, live, model, {("football:ht:-1", "not_lose")},
                                              cfg(require_value=False))}
        self.assertEqual(evs["not_lose"].decision, "alert")

    def test_basketball_never_alerts(self):
        m = parse_match("basketball", {"event_key": "b1", "event_live": "1", "event_home_team": "A",
                                       "event_away_team": "B", "event_status": "Quarter 3",
                                       "event_final_result": "60 - 66"})
        ev = evaluate(m, Quote({"first": 0.85, "second": 0.15}, {"first": 1.15, "second": 6}), None,
                      self.model, self.approved, cfg())[0]
        self.assertEqual((ev.decision, ev.state), ("shadow", "basketball:q3:-6-10"))


class FakeAllSports:
    def __init__(self, live=None):
        self.live_data = live or {"tennis": [tennis_record()], "football": [], "basketball": []}
        self.calls = []

    def live(self, sport):
        self.calls.append(("live", sport))
        return self.live_data.get(sport, [])

    def odds(self, sport, start, end):
        self.calls.append(("odds", sport))
        return {}

    def fixtures(self, sport, start, end):
        self.calls.append(("fixtures", sport))
        rec = {**tennis_record(), "event_status": "Finished", "event_winner": "Second Player"}
        return [rec] if sport == "tennis" else []


class FakeOdds:
    remaining = "999"

    def __init__(self, events):
        self._events = events
        self.odds_calls = []

    def active_keys(self, preferred):
        return ["tennis_atp_vienna"]

    def events(self, key):
        return self._events

    def odds_cost(self):
        return 1

    def odds(self, key, event_ids=None):
        self.odds_calls.append((key, event_ids))
        return [odds_event([price_book(n) for n in range(4)])]


class FakeTelegram:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail

    def send(self, message):
        if self.fail:
            from monitor.feeds import FeedError
            raise FeedError("down")
        self.sent.append(message)


class MonitorTests(unittest.TestCase):
    def make(self, dry_run=True, events=None, telegram=None, **kw):
        if hasattr(self, "folder"):
            self.folder.cleanup()
        self.folder = tempfile.TemporaryDirectory()
        db = Storage(str(Path(self.folder.name) / "m.sqlite3"))
        db.replace_history("synthetic", synthetic_history())
        db.conn.execute("INSERT INTO validations VALUES (?,?,?,?,?)", (STATE, "win", NOW.isoformat(), 1, "{}"))
        db.store_pre("odds:odds-1", {"first": .12, "second": .88, "_books": 5, "_spread": .02}, NOW - timedelta(hours=2),
                     {"first": 7.0, "second": 1.12})
        events = events if events is not None else [{"id": "odds-1", "home_team": "Cezar Cretu",
                                                     "away_team": "Laslo Djere",
                                                     "commence_time": (NOW - timedelta(minutes=35)).isoformat()}]
        self.odds = FakeOdds(events)
        self.tg = telegram or FakeTelegram()
        return Monitor(cfg(dry_run=dry_run, **kw), storage=db, allsports=FakeAllSports(), odds=self.odds,
                       telegram=self.tg)

    def tearDown(self):
        if hasattr(self, "folder"):
            self.folder.cleanup()

    def test_dry_run_archives_but_never_sends(self):
        mon = self.make(dry_run=True)
        mon.tick(NOW)
        mon.tick(NOW + timedelta(minutes=1))
        self.assertEqual(self.tg.sent, [])
        rows = mon.db.conn.execute("SELECT decision, state FROM evaluations").fetchall()
        self.assertEqual(rows, [("alert", STATE)])
        self.assertEqual(mon.db.conn.execute("SELECT COUNT(*) FROM score_snapshots").fetchone()[0], 1)

    def test_shadow_upgraded_to_alert_in_archive(self):
        mon = self.make(dry_run=True)
        mon.approved = set()
        mon.tick(NOW)
        self.assertEqual(mon.db.conn.execute("SELECT decision FROM evaluations").fetchone()[0], "shadow")
        mon.approved = {(STATE, "win")}
        mon.tick(NOW + timedelta(minutes=1))
        self.assertEqual(mon.db.conn.execute("SELECT decision, reason FROM evaluations").fetchall(),
                         [("alert", "tutte le condizioni soddisfatte")])

    def test_live_sends_once(self):
        mon = self.make(dry_run=False)
        mon.tick(NOW)
        mon.tick(NOW + timedelta(minutes=1))
        self.assertEqual(len(self.tg.sent), 1)
        self.assertIn("L. Djere", self.tg.sent[0])

    def test_telegram_failure_retried_next_cycle(self):
        mon = self.make(dry_run=False, telegram=FakeTelegram(fail=True))
        mon.tick(NOW)
        self.assertFalse(mon.db.already_alerted("tennis:live-1"))

    def test_odds_called_only_for_trailing_live_events(self):
        mon = self.make(events=[])
        mon.tick(NOW)
        self.assertEqual(self.odds.odds_calls, [])   # niente eventi => nessun credito speso
        mon = self.make()
        mon.tick(NOW)
        self.assertEqual(self.odds.odds_calls, [("tennis_atp_vienna", ["odds-1"])])
        # Chi è sotto NON era il favorito: nessun credito live speso.
        mon = self.make()
        mon.db.store_pre("odds:odds-1", {"first": .6, "second": .4}, NOW, {"first": 1.6, "second": 2.4})
        mon.tick(NOW)
        self.assertEqual(self.odds.odds_calls, [])

    def test_budget_exhausted_stops_calls(self):
        mon = self.make(max_requests_day=1)
        mon.tick(NOW)
        mon.tick(NOW + timedelta(minutes=1))
        self.assertEqual(len(self.odds.odds_calls), 1)

    def test_results_resolved_for_calibration(self):
        mon = self.make()
        mon.tick(NOW)
        mon.last_resolve = datetime.min.replace(tzinfo=timezone.utc)
        mon.resolve_results(NOW + timedelta(hours=4))
        rows = mon.db.resolved_evaluations()
        self.assertEqual([(r["winner"], r["target_side"]) for r in rows], [("second", "second")])

    def test_prematch_keeps_first_and_last(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Storage(str(Path(folder) / "m.sqlite3"))
            db.store_pre("e", {"first": .8}, NOW, {"first": 1.2})
            db.store_pre("e", {"first": .85}, NOW + timedelta(hours=1), {"first": 1.15})
            self.assertEqual(db.pre("e"), {"first": .85})
            first = db.conn.execute("SELECT prob FROM prematch WHERE event_id='e'").fetchone()[0]
            self.assertEqual(json.loads(first), {"first": .8})

    def test_context_must_be_sourced_fresh(self):
        m = parse_match("tennis", tennis_record())
        with tempfile.TemporaryDirectory() as folder:
            f = Path(folder) / "c.json"
            f.write_text(json.dumps({"tennis:live-1": {"verified_at": NOW.isoformat(), "injury": "clear",
                                                       "fatigue": "low", "sources": ["https://example.org/x"]}}))
            self.assertEqual(trusted_context(str(f), m, NOW)["injury"], "clear")
            self.assertEqual(trusted_context(str(f), m, NOW + timedelta(days=2)), {})


if __name__ == "__main__":
    unittest.main()
