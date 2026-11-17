import os
from dataclasses import dataclass


def boolean_env(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _list(key: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in os.environ.get(key, default).split(",") if x.strip())


@dataclass(frozen=True)
class Config:
    allsports_key: str
    odds_key: str
    telegram_token: str
    telegram_chat: str
    poll_seconds: int
    threshold: float
    min_books: int
    min_pre_probability: float
    max_tennis_prematch_odds: float
    max_odds_age: int
    max_spread: float
    watch_keys: tuple[str, ...]
    auto_tennis_limit: int
    max_requests_day: int
    regions: str
    dry_run: bool
    db_path: str
    context_file: str
    # Pianificazione delle chiamate a pagamento
    scores_provider: str = "espn"
    betfair_app_key: str = ""
    betfair_username: str = ""
    betfair_password: str = ""
    betfair_jurisdiction: str = "it"
    betfair_min_matched: float = 200.0
    betfair_max_rel_spread: float = 0.10
    espn_leagues: tuple[tuple[str, tuple[str, ...]], ...] = ()
    espn_idle_refresh: int = 900
    prematch_min_books: int = 1
    prematch_refresh: int = 3600
    events_refresh: int = 900
    use_allsports_odds: bool = True
    collect_all_live_odds: bool = False
    # Modello calibrato e regole di decisione
    model_bandwidth: float = 0.05
    model_min_sample: int = 150
    model_z: float = 1.2816
    validation_min_alerts: int = 30
    validation_max_gap: float = 0.05
    require_live_market: bool = True
    require_value: bool = True
    min_edge: float = 0.02
    max_model_market_gap: float = 1.0
    model_weight: float = 0.5
    tennis_model_tiers: tuple[str, ...] = ("atp", "wta")
    tennis_max_games_into_set: int = 4
    football_ht_tolerance: int = 0
    require_verified_context: bool = False
    heartbeat_file: str = "/tmp/heartbeat"

    @classmethod
    def from_env(cls) -> "Config":
        e = os.environ.get
        return cls(
            allsports_key=e("ALLSPORTS_API_KEY", ""),
            odds_key=e("ODDS_API_KEY", ""),
            telegram_token=e("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat=e("TELEGRAM_CHAT_ID", ""),
            poll_seconds=max(60, int(e("POLL_SECONDS", "60"))),
            threshold=float(e("ALERT_THRESHOLD", "0.70")),
            min_books=max(2, int(e("MIN_BOOKMAKERS", "3"))),
            min_pre_probability=float(e("MIN_PREMATCH_PROBABILITY", "0.62")),
            max_tennis_prematch_odds=float(e("MAX_TENNIS_PREMATCH_ODDS", "1.20")),
            max_odds_age=int(e("MAX_ODDS_AGE_SECONDS", "180")),
            max_spread=float(e("MAX_BOOKMAKER_SPREAD", "0.10")),
            watch_keys=_list("WATCH_SPORT_KEYS", "basketball_nba"),
            auto_tennis_limit=max(0, int(e("MAX_AUTO_TENNIS_KEYS", "40"))),
            max_requests_day=max(1, int(e("MAX_ODDS_REQUESTS_PER_DAY", "500"))),
            regions=e("ODDS_REGIONS", "eu"),
            dry_run=boolean_env("DRY_RUN", True),
            db_path=e("DB_PATH", "data/monitor.sqlite3"),
            context_file=e("CONTEXT_FILE", "context.json"),
            scores_provider=e("SCORES_PROVIDER", "espn").strip().lower(),
            betfair_app_key=e("BETFAIR_APP_KEY", ""),
            betfair_username=e("BETFAIR_USERNAME", ""),
            betfair_password=e("BETFAIR_PASSWORD", ""),
            betfair_jurisdiction=e("BETFAIR_JURISDICTION", "it").strip().lower(),
            betfair_min_matched=float(e("BETFAIR_MIN_MATCHED", "200")),
            betfair_max_rel_spread=float(e("BETFAIR_MAX_REL_SPREAD", "0.10")),
            espn_leagues=(("football", _list("ESPN_SOCCER_LEAGUES",
                                             "ita.1,ita.2,eng.1,esp.1,ger.1,fra.1,uefa.champions,uefa.europa")),
                          ("basketball", _list("ESPN_BASKETBALL_LEAGUES", "nba")),
                          ("tennis", _list("ESPN_TENNIS_LEAGUES", "atp,wta"))),
            espn_idle_refresh=max(300, int(e("ESPN_IDLE_REFRESH_SECONDS", "900"))),
            prematch_min_books=max(1, int(e("PREMATCH_MIN_BOOKMAKERS", "1"))),
            prematch_refresh=max(600, int(e("PREMATCH_REFRESH_SECONDS", "3600"))),
            events_refresh=max(120, int(e("ODDS_EVENTS_REFRESH_SECONDS", "900"))),
            use_allsports_odds=boolean_env("USE_ALLSPORTS_ODDS", True),
            collect_all_live_odds=boolean_env("COLLECT_ALL_LIVE_ODDS", False),
            model_bandwidth=float(e("MODEL_BANDWIDTH", "0.05")),
            model_min_sample=int(e("MODEL_MIN_SAMPLE", "150")),
            model_z=float(e("MODEL_Z", "1.2816")),
            validation_min_alerts=int(e("VALIDATION_MIN_ALERTS", "30")),
            validation_max_gap=float(e("VALIDATION_MAX_GAP", "0.05")),
            require_live_market=boolean_env("REQUIRE_LIVE_MARKET", True),
            require_value=boolean_env("REQUIRE_VALUE", True),
            min_edge=float(e("MIN_EDGE", "0.02")),
            max_model_market_gap=float(e("MAX_MODEL_MARKET_GAP", "1.0")),
            model_weight=float(e("MODEL_WEIGHT", "0.5")),
            tennis_model_tiers=_list("TENNIS_MODEL_TIERS", "atp,wta"),
            tennis_max_games_into_set=int(e("TENNIS_MAX_GAMES_INTO_SET", "4")),
            football_ht_tolerance=int(e("FOOTBALL_HT_TOLERANCE_MIN", "0")),
            require_verified_context=boolean_env("REQUIRE_VERIFIED_CONTEXT", False),
            heartbeat_file=e("HEARTBEAT_FILE", "/tmp/heartbeat"),
        )

    def validate(self, live: bool) -> None:
        if not 0.5 <= self.threshold < 1.0:
            raise ValueError("ALERT_THRESHOLD deve essere fra 0.50 e 1.00")
        if not 0 < self.max_odds_age <= 600:
            raise ValueError("MAX_ODDS_AGE_SECONDS deve essere da 1 a 600")
        if not 1 < self.max_tennis_prematch_odds <= 3:
            raise ValueError("MAX_TENNIS_PREMATCH_ODDS deve essere >1 e <=3")
        if not 0 <= self.max_spread <= 0.2:
            raise ValueError("MAX_BOOKMAKER_SPREAD deve essere da 0 a 0.20")
        if not 0.01 <= self.model_bandwidth <= 0.2:
            raise ValueError("MODEL_BANDWIDTH deve essere da 0.01 a 0.20")
        if self.model_min_sample < 30:
            raise ValueError("MODEL_MIN_SAMPLE deve essere almeno 30")
        if not 0 <= self.model_weight <= 1:
            raise ValueError("MODEL_WEIGHT deve essere fra 0 (solo mercato) e 1 (solo storico)")
        if self.model_z < 0.84:
            raise ValueError("MODEL_Z troppo basso: almeno 0.84 (80% unilaterale)")
        if not 0 <= self.football_ht_tolerance <= 10:
            raise ValueError("FOOTBALL_HT_TOLERANCE_MIN deve essere da 0 a 10")
        if self.scores_provider not in {"espn", "allsports"}:
            raise ValueError("SCORES_PROVIDER deve essere espn (gratuito) o allsports")
        if live and self.scores_provider == "allsports" and not self.allsports_key:
            raise ValueError("SCORES_PROVIDER=allsports richiede ALLSPORTS_API_KEY")
        if self.betfair_app_key and not (self.betfair_username and self.betfair_password):
            raise ValueError("Con BETFAIR_APP_KEY servono anche BETFAIR_USERNAME e BETFAIR_PASSWORD")
        if live and self.require_live_market and not (self.odds_key or self.betfair_app_key):
            raise ValueError("REQUIRE_LIVE_MARKET=true richiede una fonte di quote live: BETFAIR_APP_KEY "
                             "(gratuita) o ODDS_API_KEY; altrimenti imposta REQUIRE_LIVE_MARKET=false")
        if live and not self.dry_run and not (self.telegram_token and self.telegram_chat):
            raise ValueError("Imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
