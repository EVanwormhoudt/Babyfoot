import os
from urllib.parse import quote
from zoneinfo import ZoneInfo

from pydantic import BaseModel

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def parse_cors_origins(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_CORS_ORIGINS
    parsed = [origin.strip().strip("\"'") for origin in value.split(",") if origin.strip()]
    return parsed or DEFAULT_CORS_ORIGINS


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_database_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    db_name = os.getenv("POSTGRES_DB", "babyfoot")
    db_user = os.getenv("POSTGRES_USER", "babyfoot_app")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")

    auth = quote(db_user, safe="")
    if db_password:
        auth = f"{auth}:{quote(db_password, safe='')}"
    return f"postgresql+psycopg2://{auth}@{db_host}:{db_port}/{quote(db_name, safe='')}"


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    DATABASE_URL: str = build_database_url()

    CORS_ORIGINS: list[str] = parse_cors_origins(os.getenv("CORS_ORIGINS"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")
    AUTO_POPULATE_IF_EMPTY: bool = parse_bool(os.getenv("AUTO_POPULATE_IF_EMPTY"), True)
    POPULATE_SOURCE_URL: str = os.getenv("POPULATE_SOURCE_URL", "https://babyfoot.chamrai.fr")
    POPULATE_START_YEAR: int = int(os.getenv("POPULATE_START_YEAR", "2018"))
    POPULATE_START_MONTH: int = int(os.getenv("POPULATE_START_MONTH", "11"))
    NAMES_PRIVACY_PASSWORD: str | None = os.getenv("NAMES_PRIVACY_PASSWORD") or None
    NAMES_PRIVACY_SESSION_SECRET: str | None = os.getenv("NAMES_PRIVACY_SESSION_SECRET") or os.getenv(
        "NAMES_PRIVACY_PASSWORD"
    ) or None
    NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS: int = int(
        os.getenv("NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS", str(60 * 60 * 24 * 30))
    )
    NAMES_VISIBLE_IPS: list[str] = parse_csv(os.getenv("NAMES_VISIBLE_IPS"))
    NAMES_TRUSTED_PROXY_IPS: list[str] = parse_csv(os.getenv("NAMES_TRUSTED_PROXY_IPS"))

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


settings = Settings()
