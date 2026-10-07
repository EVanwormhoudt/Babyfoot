"""Running match ratings for display, separate from the daily Elo baseline."""

from datetime import timedelta

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from ..db.models import Game, GamePlayerRatingChange
from ..schemas import GameRead
from ..settings import settings
from .custom_elo import _normalize_ts


def add_running_ratings(games: list[GameRead], session: Session) -> list[GameRead]:
    days = {
        _normalize_ts(game.game_timestamp, settings.tz).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        for game in games if game.rating_changes
    }
    if not days:
        return games

    player_ids = {change.player_id for game in games for change in game.rating_changes}
    # Include earlier matches outside the requested page or player filter.
    rows = session.exec(
        select(GamePlayerRatingChange, Game.game_timestamp)
        .join(Game, Game.id == GamePlayerRatingChange.game_id)
        .where(
            GamePlayerRatingChange.player_id.in_(player_ids),
            or_(*[
                and_(Game.game_timestamp >= day, Game.game_timestamp < day + timedelta(days=1))
                for day in days
            ]),
        )
        .order_by(Game.game_timestamp.asc(), Game.id.asc())
    ).all()

    accumulated: dict[tuple, float] = {}
    transitions: dict[tuple, tuple[float, float]] = {}
    for change, timestamp in rows:
        day = _normalize_ts(timestamp, settings.tz).date()
        key = (day, change.player_id, change.rating_type)
        earlier_delta = accumulated.get(key, 0.0)
        before = change.mu_before + earlier_delta
        transitions[(change.game_id, change.player_id, change.rating_type)] = (
            before, before + change.delta_mu,
        )
        accumulated[key] = earlier_delta + change.delta_mu

    for game in games:
        for change in game.rating_changes:
            transition = transitions.get((game.id, change.player_id, change.rating_type))
            if transition is not None:
                change.running_mu_before, change.running_mu_after = transition
    return games
