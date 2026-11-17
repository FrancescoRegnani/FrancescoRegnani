import os
from dataclasses import dataclass


def boolean_env(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).lower() in {"1", "true", "yes", "on"}


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

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            allsports_key=os.environ.get("ALLSPORTS_API_KEY", ""),
            odds_key=os.environ.get("ODDS_API_KEY", ""),
            telegram_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat=os.environ.get("TELEGRAM_CHAT_ID", ""),
            poll_seconds=max(60, int(os.environ.get("POLL_SECONDS", "60"))),
            threshold=float(os.environ.get("ALERT_THRESHOLD", "0.70")),
            min_books=max(2, int(os.environ.get("MIN_BOOKMAKERS", "3"))),
            min_pre_probability=float(os.environ.get("MIN_PREMATCH_PROBABILITY", "0.62")),
            max_tennis_prematch_odds=float(os.environ.get("MAX_TENNIS_PREMATCH_ODDS", "1.20")),
            max_odds_age=int(os.environ.get("MAX_ODDS_AGE_SECONDS", "180")),
            max_spread=float(os.environ.get("MAX_BOOKMAKER_SPREAD", "0.10")),
            watch_keys=tuple(x.strip() for x in os.environ.get("WATCH_SPORT_KEYS", "basketball_nba").split(",") if x.strip()),
            auto_tennis_limit=max(0, int(os.environ.get("MAX_AUTO_TENNIS_KEYS", "8"))),
            max_requests_day=max(1, int(os.environ.get("MAX_ODDS_REQUESTS_PER_DAY", "4000"))),
            regions=os.environ.get("ODDS_REGIONS", "eu"),
            dry_run=boolean_env("DRY_RUN", True),
            db_path=os.environ.get("DB_PATH", "data/monitor.sqlite3"),
            context_file=os.environ.get("CONTEXT_FILE", "context.json"),
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
        if live and not (self.allsports_key and self.odds_key):
            raise ValueError("Servono ALLSPORTS_API_KEY e ODDS_API_KEY per i dati verificati")
        if live and not self.dry_run and not (self.telegram_token and self.telegram_chat):
            raise ValueError("Imposta TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
