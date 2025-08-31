import os
from zoneinfo import ZoneInfo

from pydantic import BaseModel


class Settings(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    CORS_ORIGINS: list[str] = (
        os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if os.getenv("CORS_ORIGINS")
        else ["http://localhost:5173"]
    )
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Paris")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


settings = Settings()
