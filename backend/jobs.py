from __future__ import annotations

from datetime import datetime, date, timedelta
import logging
from typing import Dict, Iterable

from sqlalchemy import update, func, literal
from sqlalchemy import desc, asc
from sqlmodel import Session, select

from backend.db.session import engine
from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.db import CurrentPlayerRank, Game, PlayerRatingHistory
from backend.settings import settings

logger = logging.getLogger(__name__)
DAILY_SNAPSHOT_TYPES = ("overall", "monthly", "yearly")

monthly_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_monthly), asc(CurrentPlayerRank.sigma_monthly))
)
yearly_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_yearly), asc(CurrentPlayerRank.sigma_yearly))
)
overall_rank_expr = func.dense_rank().over(
    order_by=(desc(CurrentPlayerRank.mu_overall), asc(CurrentPlayerRank.sigma_overall))
)


def _rank_expr_for(rank_type: str):
    if rank_type == "monthly":
        return monthly_rank_expr
    if rank_type == "yearly":
        return yearly_rank_expr
    if rank_type == "overall":
        return overall_rank_expr
    raise ValueError(f"Unsupported rank_type: {rank_type}")


def _has_snapshot_changed(
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


def _has_overall_snapshot_changed(
        current_mu: float,
        current_sigma: float,
        previous_mu: float | None,
        previous_sigma: float | None,
        *,
        tol: float = 1e-9,
) -> bool:
    return _has_snapshot_changed(
        current_mu,
        current_sigma,
        previous_mu,
        previous_sigma,
        tol=tol,
    )


def _latest_snapshots_by_player(
        session: Session,
        rank_type: str,
) -> Dict[int, tuple[float | None, float | None]]:
    ranked = (
        select(
            PlayerRatingHistory.player_id.label("player_id"),
            PlayerRatingHistory.mu.label("mu"),
            PlayerRatingHistory.sigma.label("sigma"),
            func.row_number().over(
                partition_by=PlayerRatingHistory.player_id,
                order_by=(desc(PlayerRatingHistory.date), desc(PlayerRatingHistory.update_id)),
            ).label("rn"),
        )
        .where(PlayerRatingHistory.rank_type == rank_type)
        .subquery()
    )

    rows = session.exec(
        select(ranked.c.player_id, ranked.c.mu, ranked.c.sigma)
        .where(ranked.c.rn == 1)
    ).all()

    latest: Dict[int, tuple[float | None, float | None]] = {}
    for row in rows:
        latest[int(row.player_id)] = (
            float(row.mu) if row.mu is not None else None,
            float(row.sigma) if row.sigma is not None else None,
        )
    return latest


def _latest_overall_snapshots_by_player(session: Session) -> Dict[int, tuple[float | None, float | None]]:
    return _latest_snapshots_by_player(session, "overall")


def _build_daily_snapshot_rows(
        *,
        candidates: Iterable[dict[str, float | int]],
        latest_by_player: Dict[int, tuple[float | None, float | None]],
        snapshot_date: date,
        rank_type: str,
) -> list[dict[str, float | int | str | date]]:
    rows_to_insert: list[dict[str, float | int | str | date]] = []

    for candidate in candidates:
        player_id = int(candidate["player_id"])
        current_mu = float(candidate["mu"])
        current_sigma = float(candidate["sigma"])
        rank = int(candidate["rank"])

        previous_mu, previous_sigma = latest_by_player.get(player_id, (None, None))
        if not _has_snapshot_changed(current_mu, current_sigma, previous_mu, previous_sigma):
            continue

        rows_to_insert.append(
            {
                "player_id": player_id,
                "mu": current_mu,
                "sigma": current_sigma,
                "date": snapshot_date,
                "rank": rank,
                "rank_type": rank_type,
            }
        )

    return rows_to_insert


def _build_daily_overall_snapshot_rows(
        *,
        candidates: Iterable[dict[str, float | int]],
        latest_by_player: Dict[int, tuple[float | None, float | None]],
        snapshot_date: date,
) -> list[dict[str, float | int | str | date]]:
    return _build_daily_snapshot_rows(
        candidates=candidates,
        latest_by_player=latest_by_player,
        snapshot_date=snapshot_date,
        rank_type="overall",
    )


def _snapshot_date_expr(snapshot_date: date):
    return literal(snapshot_date.isoformat()).cast(PlayerRatingHistory.date.type)


def _rank_type_expr(rank_type: str):
    return literal(rank_type)


def _snapshot_daily_ratings(session: Session, *, snapshot_date: date) -> int:
    rows_to_insert: list[dict[str, float | int | str | date]] = []
    for rank_type in DAILY_SNAPSHOT_TYPES:
        current_rows = session.exec(
            select(
                CurrentPlayerRank.player_id.label("player_id"),
                getattr(CurrentPlayerRank, f"mu_{rank_type}").label("mu"),
                getattr(CurrentPlayerRank, f"sigma_{rank_type}").label("sigma"),
                _rank_expr_for(rank_type).label("rank"),
            )
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
        rows_to_insert.extend(
            _build_daily_snapshot_rows(
                candidates=candidates,
                latest_by_player=_latest_snapshots_by_player(session, rank_type),
                snapshot_date=snapshot_date,
                rank_type=rank_type,
            )
        )

    _upsert_snapshot_rows(session, rows_to_insert)
    return len(rows_to_insert)


def _latest_snapshot_dates_by_type(session: Session) -> dict[str, date | None]:
    rows = session.exec(
        select(PlayerRatingHistory.rank_type, func.max(PlayerRatingHistory.date))
        .where(PlayerRatingHistory.rank_type.in_(DAILY_SNAPSHOT_TYPES))
        .group_by(PlayerRatingHistory.rank_type)
    ).all()
    latest = {rank_type: None for rank_type in DAILY_SNAPSHOT_TYPES}
    for rank_type, latest_date in rows:
        latest[str(rank_type)] = latest_date
    return latest


def _normalize_game_timestamp(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=settings.tz)
    return ts.astimezone(settings.tz)


def snapshot_missing_daily_ratings_if_safe(
        session: Session,
        *,
        now: datetime | None = None,
        warn_if_unsafe: bool = True,
) -> int:
    now = now or datetime.now(tz=settings.tz)
    latest_daily_snapshot_date = now.date() - timedelta(days=1)
    latest_dates = _latest_snapshot_dates_by_type(session)
    if all(
            latest_date is not None and latest_date >= latest_daily_snapshot_date
            for latest_date in latest_dates.values()
    ):
        return 0

    latest_game_ts = _normalize_game_timestamp(
        session.exec(select(func.max(Game.game_timestamp))).one()
    )
    if latest_game_ts is not None and latest_game_ts.date() != latest_daily_snapshot_date:
        if warn_if_unsafe:
            logger.warning(
                "Daily rating snapshots are stale for %s, but latest game is on %s; "
                "run backend.database_setup.rebuild_ratings_and_history to backfill safely",
                latest_daily_snapshot_date,
                latest_game_ts.date(),
            )
        return 0

    return _snapshot_daily_ratings(session, snapshot_date=latest_daily_snapshot_date)


def _upsert_snapshot_rows(session: Session, rows_to_insert: list[dict[str, float | int | str | date]]) -> None:
    if not rows_to_insert:
        return

    for row in rows_to_insert:
        existing = session.exec(
            select(PlayerRatingHistory).where(
                PlayerRatingHistory.player_id == int(row["player_id"]),
                PlayerRatingHistory.rank_type == str(row["rank_type"]),
                PlayerRatingHistory.date == row["date"],
            )
        ).first()
        if existing is None:
            session.add(PlayerRatingHistory(**row))
        else:
            existing.mu = float(row["mu"])
            existing.sigma = float(row["sigma"])
            existing.rank = int(row["rank"])


def _reset_monthly_current_ratings(session: Session, *, now: datetime) -> None:
    session.execute(
        update(CurrentPlayerRank)
        .values(
            mu_monthly=DEFAULT_RATING,
            sigma_monthly=DEFAULT_SIGMA,
            last_updated=now,
        )
    )


def _reset_yearly_current_ratings(session: Session, *, now: datetime) -> None:
    session.execute(
        update(CurrentPlayerRank)
        .values(
            mu_yearly=DEFAULT_RATING,
            sigma_yearly=DEFAULT_SIGMA,
            last_updated=now,
        )
    )


def snapshot_daily_ratings_and_roll_periods():
    now = datetime.now(tz=settings.tz)
    today = now.date()
    snapshot_date = today - timedelta(days=1)

    with Session(engine) as session:
        row_count = _snapshot_daily_ratings(session, snapshot_date=snapshot_date)

        if today.day == 1:
            _reset_monthly_current_ratings(session, now=now)
        if today.month == 1 and today.day == 1:
            _reset_yearly_current_ratings(session, now=now)

        session.commit()

    logger.info(
        "Daily ratings snapshotted for %s rows on %s%s%s",
        row_count,
        snapshot_date,
        "; monthly reset" if today.day == 1 else "",
        "; yearly reset" if today.month == 1 and today.day == 1 else "",
    )


def snapshot_and_reset_monthly():
    now = datetime.now(tz=settings.tz)

    with Session(engine) as session:
        _reset_monthly_current_ratings(session, now=now)
        session.commit()

    logger.info("Monthly ratings reset")


def snapshot_and_reset_yearly():
    now = datetime.now(tz=settings.tz)

    with Session(engine) as session:
        _reset_yearly_current_ratings(session, now=now)
        session.commit()

    logger.info("Yearly ratings reset")


def snapshot_overall_daily_if_changed():
    now = datetime.now(tz=settings.tz)
    snapshot_date = now.date() - timedelta(days=1)

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
            snapshot_date=snapshot_date,
        )

        if not rows_to_insert:
            logger.info("Daily overall snapshot skipped because no ratings changed for %s", snapshot_date)
            return

        _upsert_snapshot_rows(session, rows_to_insert)
        session.commit()

    logger.info("Daily overall ratings snapshotted for %s players on %s", len(rows_to_insert), snapshot_date)
