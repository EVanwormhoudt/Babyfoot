from __future__ import annotations

from datetime import datetime, date
from typing import Dict, Iterable

from sqlalchemy import update, insert, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import desc, asc
from sqlmodel import Session

from backend.db.session import engine
from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.db import CurrentPlayerRank, PlayerRatingHistory
from backend.settings import settings

monthly_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_monthly), asc(CurrentPlayerRank.sigma_monthly))
)
yearly_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_yearly), asc(CurrentPlayerRank.sigma_yearly))
)
overall_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_overall), asc(CurrentPlayerRank.sigma_overall))
)


def _has_overall_snapshot_changed(
        current_mu: float,
        current_sigma: float,
        previous_mu: float | None,
        previous_sigma: float | None,
        *,
        tol: float = 1e-9,
) -> bool:
    if previous_mu is None or previous_sigma is None:
        return True
    return (
            abs(float(current_mu) - float(previous_mu)) > tol
            or abs(float(current_sigma) - float(previous_sigma)) > tol
    )


def _latest_overall_snapshots_by_player(session: Session) -> Dict[int, tuple[float | None, float | None]]:
    ranked = (
        session.query(
            PlayerRatingHistory.player_id.label("player_id"),
            PlayerRatingHistory.mu.label("mu"),
            PlayerRatingHistory.sigma.label("sigma"),
            func.row_number().over(
                partition_by=PlayerRatingHistory.player_id,
                order_by=(desc(PlayerRatingHistory.date), desc(PlayerRatingHistory.update_id)),
            ).label("rn"),
        )
        .filter(PlayerRatingHistory.rank_type == "overall")
        .subquery()
    )

    rows = (
        session.query(ranked.c.player_id, ranked.c.mu, ranked.c.sigma)
        .filter(ranked.c.rn == 1)
        .all()
    )

    latest: Dict[int, tuple[float | None, float | None]] = {}
    for row in rows:
        latest[int(row.player_id)] = (
            float(row.mu) if row.mu is not None else None,
            float(row.sigma) if row.sigma is not None else None,
        )
    return latest


def _build_daily_overall_snapshot_rows(
        *,
        candidates: Iterable[dict[str, float | int]],
        latest_by_player: Dict[int, tuple[float | None, float | None]],
        snapshot_date: date,
) -> list[dict[str, float | int | str | date]]:
    rows_to_insert: list[dict[str, float | int | str | date]] = []

    for candidate in candidates:
        player_id = int(candidate["player_id"])
        current_mu = float(candidate["mu"])
        current_sigma = float(candidate["sigma"])
        rank = int(candidate["rank"])

        previous_mu, previous_sigma = latest_by_player.get(player_id, (None, None))
        if not _has_overall_snapshot_changed(current_mu, current_sigma, previous_mu, previous_sigma):
            continue

        rows_to_insert.append(
            {
                "player_id": player_id,
                "mu": current_mu,
                "sigma": current_sigma,
                "date": snapshot_date,
                "rank": rank,
                "rank_type": "overall",
            }
        )

    return rows_to_insert


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
                monthly_rank_expr.label("rank"),
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


def snapshot_overall_daily_if_changed():
    today = datetime.now(tz=settings.tz).date()

    with Session(engine) as session:
        latest_by_player = _latest_overall_snapshots_by_player(session)
        current_rows = session.query(
            CurrentPlayerRank.player_id.label("player_id"),
            CurrentPlayerRank.mu_overall.label("mu"),
            CurrentPlayerRank.sigma_overall.label("sigma"),
            overall_rank_expr.label("rank"),
        ).all()

        candidates = [
            {
                "player_id": int(row.player_id),
                "mu": float(row.mu),
                "sigma": float(row.sigma),
                "rank": int(row.rank),
            }
            for row in current_rows
        ]

        rows_to_insert = _build_daily_overall_snapshot_rows(
            candidates=candidates,
            latest_by_player=latest_by_player,
            snapshot_date=today,
        )

        if not rows_to_insert:
            print("ℹ️ Daily overall snapshot skipped (no Elo changes)")
            return

        try:
            insert_stmt = pg_insert(PlayerRatingHistory).values(rows_to_insert)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["player_id", "rank_type", "date"],
                set_={
                    "mu": insert_stmt.excluded.mu,
                    "sigma": insert_stmt.excluded.sigma,
                    "rank": insert_stmt.excluded.rank,
                },
            )
            session.execute(upsert_stmt)
        except Exception:
            for row in rows_to_insert:
                existing = session.query(PlayerRatingHistory).filter(
                    PlayerRatingHistory.player_id == int(row["player_id"]),
                    PlayerRatingHistory.rank_type == str(row["rank_type"]),
                    PlayerRatingHistory.date == row["date"],
                ).first()
                if existing is None:
                    session.add(PlayerRatingHistory(**row))
                else:
                    existing.mu = float(row["mu"])
                    existing.sigma = float(row["sigma"])
                    existing.rank = int(row["rank"])

        session.commit()

    print(f"✅ Daily overall ratings snapshotted ({len(rows_to_insert)} player rows)")
