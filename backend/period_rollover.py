from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, update
from sqlmodel import Session, select

from .consts import DEFAULT_RATING, DEFAULT_SIGMA
from .db.models import CurrentPlayerRank, Game
from .settings import settings


def _normalize_ts(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=settings.tz)
    return ts.astimezone(settings.tz)


def _has_non_default_ratings(session: Session, rating_type: str) -> bool:
    row = session.exec(
        select(CurrentPlayerRank.player_id)
        .where(
            or_(
                getattr(CurrentPlayerRank, f"mu_{rating_type}") != DEFAULT_RATING,
                getattr(CurrentPlayerRank, f"sigma_{rating_type}") != DEFAULT_SIGMA,
            )
        )
        .limit(1)
    ).first()
    return row is not None


def ensure_current_period_ratings(
        session: Session,
        *,
        now: datetime | None = None,
) -> bool:
    """
    Catch up monthly/yearly current ratings when the scheduled rollover was missed.

    The decision is based on the latest recorded game period instead of
    `CurrentPlayerRank.last_updated`, because inactive players can legitimately keep
    an older `last_updated` even after the current month has already started.
    """
    now = now or datetime.now(tz=settings.tz)
    latest_game_ts = _normalize_ts(
        session.exec(select(func.max(Game.game_timestamp))).one()
    )

    if latest_game_ts is None:
        return False

    changed = False

    needs_monthly_reset = (latest_game_ts.year, latest_game_ts.month) != (now.year, now.month)
    if needs_monthly_reset and _has_non_default_ratings(session, "monthly"):
        session.execute(
            update(CurrentPlayerRank)
            .values(
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                last_updated=now,
            )
        )
        changed = True

    needs_yearly_reset = latest_game_ts.year != now.year
    if needs_yearly_reset and _has_non_default_ratings(session, "yearly"):
        session.execute(
            update(CurrentPlayerRank)
            .values(
                mu_yearly=DEFAULT_RATING,
                sigma_yearly=DEFAULT_SIGMA,
                last_updated=now,
            )
        )
        changed = True

    return changed
