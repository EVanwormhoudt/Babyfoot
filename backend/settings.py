import os
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


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/babyfoot",
    )

    CORS_ORIGINS: list[str] = parse_cors_origins(os.getenv("CORS_ORIGINS"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")
    AUTO_POPULATE_IF_EMPTY: bool = parse_bool(os.getenv("AUTO_POPULATE_IF_EMPTY"), True)
    POPULATE_SOURCE_URL: str = os.getenv("POPULATE_SOURCE_URL", "https://babyfoot.chamrai.fr")
    POPULATE_START_YEAR: int = int(os.getenv("POPULATE_START_YEAR", "2018"))
    POPULATE_START_MONTH: int = int(os.getenv("POPULATE_START_MONTH", "11"))

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


settings = Settings()
