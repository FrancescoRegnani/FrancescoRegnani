"""Riga di comando.

  python -m monitor run                      # servizio (DRY_RUN=true di default)
  python -m monitor demo                     # esempio offline con dati SINTETICI
  python -m monitor import-history --sport football FILE.csv [...]
  python -m monitor import-history --sport tennis --tier atp FILE.csv [...]
  python -m monitor import-live              # usa come storico le valutazioni live con esito noto
  python -m monitor validate --cutoff 2025-07-01
  python -m monitor report                   # calibrazione delle valutazioni archiviate
  python -m monitor status
  python -m monitor test-telegram            # invia un messaggio di prova al bot
  python -m monitor test-betfair             # login Betfair e conteggio mercati (nessuna scommessa)
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
from datetime import date, datetime, timedelta, timezone

from .app import ROME, Monitor, format_alert, sport_for_key, trusted_context  # noqa: F401  (riesportati)
from .config import Config
from .decision import Quote, evaluate
from .engine import parse_match
from .history import import_file
from .model import EmpiricalModel, Example, validate, wilson
from .storage import Storage


def _pct(x) -> str:
    return "  n/d" if x is None else f"{x:6.1%}"


def cmd_import_history(cfg: Config, args) -> None:
    db = Storage(cfg.db_path)
    for path in args.files:
        examples, skipped = import_file(path, args.sport, tier=args.tier or "")
        db.replace_history(f"{args.sport}:{args.tier or ''}:{path}", examples)
        print(f"{path}: {len(examples)} situazioni di svantaggio del favorito importate, {skipped} righe scartate")
    print("Le validazioni precedenti sono state azzerate: esegui `python -m monitor validate --cutoff AAAA-MM-GG`.")


def cmd_import_live(cfg: Config) -> None:
    db = Storage(cfg.db_path)
    examples = []
    for r in db.resolved_evaluations():
        if r["outcome"] != "win" or r["pre_prob"] is None:
            continue   # un esempio per partita/stato; win e not_lose si ricavano dallo stesso esito
        winner, target = r["winner"], r["target_side"]
        examples.append(Example(r["state"], r["first_seen"][:10], r["pre_prob"], int(winner == target),
                                int(winner in (target, "draw")), "live-collected"))
    db.replace_history("live-collected", examples)
    print(f"{len(examples)} situazioni live con esito noto inserite nello storico (fonte live-collected).")


def cmd_validate(cfg: Config, args) -> None:
    db = Storage(cfg.db_path)
    examples = db.history()
    if not examples:
        print("Storico vuoto: importa prima i dati (import-history / import-live).")
        return
    results = validate(examples, args.cutoff, cfg.threshold, bandwidth=cfg.model_bandwidth,
                       min_sample=cfg.model_min_sample, z=cfg.model_z, min_alerts=cfg.validation_min_alerts,
                       max_gap=cfg.validation_max_gap)
    db.save_validations(results, datetime.now(timezone.utc))
    print(f"Validazione fuori tempo: addestramento < {args.cutoff} <= test. Soglia {cfg.threshold:.0%} "
          f"(alert se limite inferiore > soglia).")
    for v in results:
        print(f"\n[{'PROMOSSO' if v.passed else 'NON promosso'}] {v.state} / {v.outcome}: {v.note}")
        print(f"  test {v.n_test}, coperti {v.covered}, Brier {v.brier if v.brier is None else round(v.brier, 4)}, "
              f"log loss {v.logloss if v.logloss is None else round(v.logloss, 4)}")
        print(f"  alert simulati {v.alerts}, riusciti {v.hits}, predetto medio {_pct(v.mean_predicted)}, "
              f"limite inf. osservato {_pct(v.alert_lower)}")
        for label, n, pred, obs in v.buckets:
            print(f"    fascia {label:>9}: n={n:5d} predetto {pred:6.1%} osservato {obs:6.1%}")


def cmd_report(cfg: Config) -> None:
    db = Storage(cfg.db_path)
    rows = db.resolved_evaluations()
    if not rows:
        print("Nessuna valutazione con esito finale ancora disponibile.")
        return
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for r in rows:
        groups.setdefault((r["decision"], r["state"], r["outcome"]), []).append(r)
    print("decisione | stato | esito | n | riuscite | storico medio | mercato live medio | finale media")
    for (decision, state, outcome), items in sorted(groups.items()):
        hits = [int(r["winner"] == r["target_side"] or (outcome == "not_lose" and r["winner"] == "draw"))
                for r in items]
        mp = [r["model_point"] for r in items if r["model_point"] is not None]
        lp = [r["live_prob"] for r in items if r["live_prob"] is not None]
        fp = [r["final_prob"] for r in items if r.get("final_prob") is not None]
        lo, hi = wilson(sum(hits), len(hits), 1.96)
        print(f"{decision:7} | {state:28} | {outcome:8} | {len(items):4d} | {sum(hits) / len(hits):6.1%} "
              f"[{lo:.0%}-{hi:.0%}] | {_pct(sum(mp) / len(mp) if mp else None)} | {_pct(sum(lp) / len(lp) if lp else None)} | {_pct(sum(fp) / len(fp) if fp else None)}")


def cmd_status(cfg: Config) -> None:
    db = Storage(cfg.db_path)
    today = datetime.now(timezone.utc).astimezone(ROME).strftime("%Y-%m-%d")
    print(f"Crediti The Odds API consumati oggi: {db.used_today(today)}/{cfg.max_requests_day}; "
          f"residui dichiarati dal provider: {db.get_kv('odds_api_remaining') or 'n/d'}")
    sizes: dict[str, int] = {}
    for e in db.history():
        sizes[e.state] = sizes.get(e.state, 0) + 1
    print("Storico per stato:", ", ".join(f"{k}={v}" for k, v in sorted(sizes.items())) or "vuoto")
    print("Stati/esiti promossi:", ", ".join(f"{s}/{o}" for s, o in sorted(db.approved())) or "nessuno (=> nessun alert)")
    counts = db.conn.execute("SELECT decision, COUNT(*) FROM evaluations GROUP BY decision").fetchall()
    print("Valutazioni archiviate:", dict(counts) or "nessuna")


def cmd_test_telegram(cfg: Config) -> None:
    from .feeds import FeedError, Telegram
    if not (cfg.telegram_token and cfg.telegram_chat):
        print("Mancano TELEGRAM_BOT_TOKEN e/o TELEGRAM_CHAT_ID nel file .env")
        sys.exit(1)
    try:
        Telegram(cfg.telegram_token, cfg.telegram_chat).send(
            "Odds Intelligence Live: bot collegato correttamente. Messaggio di prova, nessuna segnalazione.")
    except FeedError as exc:
        print(f"Invio non riuscito: {exc}. Controlla token, chat ID e di aver scritto /start al bot.")
        sys.exit(1)
    print("Messaggio di prova inviato: controlla Telegram.")


def cmd_test_betfair(cfg: Config) -> None:
    from .betfair import Betfair
    from .feeds import FeedError
    if not (cfg.betfair_app_key and cfg.betfair_username and cfg.betfair_password):
        print("Mancano BETFAIR_APP_KEY, BETFAIR_USERNAME o BETFAIR_PASSWORD nel file .env")
        sys.exit(1)
    bf = Betfair(cfg.betfair_app_key, cfg.betfair_username, cfg.betfair_password, cfg.betfair_jurisdiction)
    now = datetime.now(timezone.utc)
    try:
        bf.login()
        for sport in ("tennis", "football", "basketball"):
            markets = bf.catalogue(sport, now - timedelta(hours=3), now + timedelta(hours=24))
            print(f"{sport}: {len(markets)} mercati Esito finale nelle prossime 24 ore")
            if markets:
                book = bf.books([markets[0].market_id]).get(markets[0].market_id, {})
                print(f"  esempio: {markets[0].event} — stato {book.get('status')}, "
                      f"dati ritardati: {book.get('isMarketDataDelayed')}")
    except FeedError as exc:
        print(f"Betfair non raggiungibile: {exc}")
        sys.exit(1)
    print("Betfair collegato correttamente (solo lettura quote, nessuna scommessa).")


def demo() -> None:
    """Pipeline completa con dati SINTETICI: storico simulato, validazione, valutazione, messaggio."""
    rng = random.Random(7)
    start = date(2020, 1, 1)
    examples = []
    for i in range(6000):
        pre = rng.uniform(0.62, 0.95)
        win = int(rng.random() < 0.25 + 0.65 * pre)     # legge inventata, solo dimostrativa
        examples.append(Example("tennis:atp:bo3:0-1", (start + timedelta(days=i // 3)).isoformat(), pre, win, win,
                                "SINTETICO"))
    cfg = Config.from_env()
    results = validate(examples, "2024-01-01", cfg.threshold, bandwidth=cfg.model_bandwidth,
                       min_sample=cfg.model_min_sample, z=cfg.model_z, min_alerts=cfg.validation_min_alerts,
                       max_gap=cfg.validation_max_gap)
    approved = {(v.state, v.outcome) for v in results if v.passed}
    model = EmpiricalModel([e for e in examples if e.date < "2024-01-01"], bandwidth=cfg.model_bandwidth,
                           min_sample=cfg.model_min_sample, z=cfg.model_z)
    record = {"event_live": "1", "event_key": "demo-match", "event_first_player": "A. Rossi",
              "event_second_player": "B. Bianchi", "event_status": "Set 2", "country_name": "Atp Singles",
              "scores": [{"score_first": "7", "score_second": "5", "score_set": "1"},
                         {"score_first": "1", "score_second": "1", "score_set": "2"}],
              "event_game_result": "1 - 1", "league_name": "ATP Torneo di esempio (SIMULATO)"}
    match = parse_match("tennis", record)
    assert match
    pre = Quote({"first": 0.12, "second": 0.88}, {"first": 7.0, "second": 1.12}, 5, 0.02, "SINTETICO")
    live = Quote({"first": 0.27, "second": 0.73}, {"first": 3.5, "second": 1.33}, 4, 0.02, "SINTETICO")
    now = datetime.now(timezone.utc)
    print("DEMO: storico, partita e quote SINTETICI e inventati. Nessuna connessione o notifica.")
    for v in results:
        print(f"Validazione {v.state}/{v.outcome}: {v.note} (alert simulati {v.alerts}, riusciti {v.hits})")
    for ev in evaluate(match, pre, live, model, approved, cfg):
        print(f"Decisione: {ev.decision} — {ev.reason}")
        if ev.decision == "alert":
            print(format_alert(ev, now, True))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Odds Intelligence: monitor rimonte con modello calibrato")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run")
    sub.add_parser("demo")
    imp = sub.add_parser("import-history")
    imp.add_argument("--sport", choices=["football", "tennis"], required=True)
    imp.add_argument("--tier", choices=["atp", "wta", "challenger", "itf"])
    imp.add_argument("files", nargs="+")
    sub.add_parser("import-live")
    val = sub.add_parser("validate")
    val.add_argument("--cutoff", required=True, help="data AAAA-MM-GG: prima = addestramento, dopo = test")
    sub.add_parser("report")
    sub.add_parser("status")
    sub.add_parser("test-telegram")
    sub.add_parser("test-betfair")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    cfg = Config.from_env()
    command = args.command or "run"
    if command == "demo":
        demo()
    elif command == "import-history":
        cmd_import_history(cfg, args)
    elif command == "import-live":
        cmd_import_live(cfg)
    elif command == "validate":
        cmd_validate(cfg, args)
    elif command == "report":
        cmd_report(cfg)
    elif command == "status":
        cmd_status(cfg)
    elif command == "test-telegram":
        cmd_test_telegram(cfg)
    elif command == "test-betfair":
        cmd_test_betfair(cfg)
    else:
        Monitor(cfg).run()


if __name__ == "__main__":
    main()
