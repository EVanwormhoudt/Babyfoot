from fastapi import FastAPI
from datetime import datetime
from sqlmodel import Session
from backend.db.session import engine
from backend.db.models import CurrentPlayerRank
from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.settings import settings
from sqlalchemy import update

def reset_monthly_ratings():
    with Session(engine) as session:
        session.exec(
            update(CurrentPlayerRank).values(
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                last_updated=datetime.now(tz=settings.tz),
            )
        )
        session.commit()
    print("✅ Monthly ratings reset")


reset_monthly_ratings()