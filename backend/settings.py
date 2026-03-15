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


class Settings(BaseModel):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/babyfoot",
    )

    CORS_ORIGINS: list[str] = parse_cors_origins(os.getenv("CORS_ORIGINS"))
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


settings = Settings()
