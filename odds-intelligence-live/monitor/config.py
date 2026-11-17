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
    max_model_market_gap: float = 0.15
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
            max_model_market_gap=float(e("MAX_MODEL_MARKET_GAP", "0.15")),
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
        if self.model_z < 0.84:
            raise ValueError("MODEL_Z troppo basso: almeno 0.84 (80% unilaterale)")
        if not 0 <= self.football_ht_tolerance <= 10:
            raise ValueError("FOOTBALL_HT_TOLERANCE_MIN deve essere da 0 a 10")
        if live and not self.allsports_key:
            raise ValueError("Serve ALLSPORTS_API_KEY per punteggi e quote pre-partita")
        if live and self.require_live_market and not self.odds_key:
            raise ValueError("REQUIRE_LIVE_MARKET=true richiede ODDS_API_KEY")
        if live and not self.dry_run and not (self.telegram_token and self.telegram_chat):
            raise ValueError("Imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
