from datetime import datetime, date
from sqlmodel import Session
from sqlalchemy import update, insert, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert  # only if Postgres
from sqlalchemy import desc, asc
from sqlalchemy.sql import over
from backend.db.session import engine

from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.db import CurrentPlayerRank, PlayerRatingHistory
from backend.settings import settings

# --- window expressions for rank ---
# rank by mu_monthly desc, sigma_monthly asc (change if you use another rule)
rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_monthly), asc(CurrentPlayerRank.sigma_monthly))
)


def snapshot_and_reset_monthly():
    today = datetime.now(tz=settings.tz).date()

    with Session(engine) as session:
        # 1) INSERT snapshot into PlayerRatingHistory (set-based)
        base_select = (
            session.query(
                CurrentPlayerRank.player_id.label("player_id"),
                CurrentPlayerRank.mu_monthly.label("mu"),
                CurrentPlayerRank.sigma_monthly.label("sigma"),
                func.cast(func.literal(today.isoformat()), PlayerRatingHistory.date.type).label("date"),
                rank_expr.label("rank"),
                func.literal("monthly").label("rank_type"),
            )
        ).subquery()

        # Postgres: upsert to honor the unique constraint (player_id, rank_type, date)
        try:
            stmt = pg_insert(PlayerRatingHistory).from_select(
                ["player_id", "mu", "sigma", "date", "rank", "rank_type"],
                session.query(base_select)  # SELECT * FROM subquery
            ).on_conflict_do_nothing(
                index_elements=["player_id", "rank_type", "date"]
            )
            session.execute(stmt)
        except Exception:
            # DB-agnostic fallback: plain insert; if duplicates occur the unique constraint will raise
            stmt = insert(PlayerRatingHistory).from_select(
                ["player_id", "mu", "sigma", "date", "rank", "rank_type"],
                session.query(base_select)
            )
            session.execute(stmt)

        # 2) RESET monthly fields
        session.execute(
            update(CurrentPlayerRank)
            .values(
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                last_updated=datetime.now(tz=settings.tz),
            )
        )

        session.commit()

    print("✅ Monthly ratings snapshotted + reset")


def snapshot_and_reset_yearly():
    today = datetime.now(tz=settings.tz).date()

    # define your yearly rank expression (adjust columns)
    yearly_rank_expr = func.dense_rank().over(
        order_by=(desc(CurrentPlayerRank.mu_yearly), asc(CurrentPlayerRank.sigma_yearly))
    )

    with Session(engine) as session:
        base_select = (
            session.query(
                CurrentPlayerRank.player_id.label("player_id"),
                CurrentPlayerRank.mu_yearly.label("mu"),
                CurrentPlayerRank.sigma_yearly.label("sigma"),
                func.cast(func.literal(today.isoformat()), PlayerRatingHistory.date.type).label("date"),
                yearly_rank_expr.label("rank"),
                func.literal("yearly").label("rank_type"),
            )
        ).subquery()

        try:
            stmt = pg_insert(PlayerRatingHistory).from_select(
                ["player_id", "mu", "sigma", "date", "rank", "rank_type"],
                session.query(base_select)
            ).on_conflict_do_nothing(
                index_elements=["player_id", "rank_type", "date"]
            )
            session.execute(stmt)
        except Exception:
            stmt = insert(PlayerRatingHistory).from_select(
                ["player_id", "mu", "sigma", "date", "rank", "rank_type"],
                session.query(base_select)
            )
            session.execute(stmt)

        session.execute(
            update(CurrentPlayerRank)
            .values(
                mu_yearly=DEFAULT_RATING,
                sigma_yearly=DEFAULT_SIGMA,
                last_updated=datetime.now(tz=settings.tz),
            )
        )
        session.commit()

    print("✅ Yearly ratings snapshotted + reset")
