import os
import unittest
from datetime import datetime

from sqlalchemy import update
from sqlmodel import Session

from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.db.models import CurrentPlayerRank
from backend.db.session import engine
from backend.settings import settings


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


@unittest.skipUnless(
    os.getenv("RUN_DB_MUTATION_TESTS") == "1",
    "skips live database mutation helper unless RUN_DB_MUTATION_TESTS=1",
)
class ResetMonthlyRatingsTests(unittest.TestCase):
    def test_reset_monthly_ratings(self):
        reset_monthly_ratings()
