from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db.models import Game, Player, Team
from ..db.session import get_session
from ..schemas import GameRead, PlayerStats
from ..utils import get_scope_date, get_basic_stats, get_teammate_stats, get_win_streaks

router = APIRouter()


@router.get("/{player_id}/history", response_model=List[GameRead])
def get_player_games(player_id: int, session: Session = Depends(get_session)):
    if not session.get(Player, player_id):
        raise HTTPException(404, "Player not found")
    games = session.exec(
        select(Game)
        .options(selectinload(Game.teams))
        .join(Team, Team.game_id == Game.id)
        .where(Team.player_id == player_id)
        .order_by(Game.game_timestamp.desc())
    ).all()
    return games


@router.get("/{player_id}/stats", response_model=PlayerStats)
def get_player_stats(player_id: int, scope: str = Query("overall"), session: Session = Depends(get_session)):
    if not session.get(Player, player_id):
        raise HTTPException(404, "Player not found")

    since = get_scope_date(scope)

    basic = get_basic_stats(session, player_id, since)
    teammates = get_teammate_stats(session, player_id, since)
    streaks = get_win_streaks(session, player_id, since)

    best = max(teammates, key=lambda x: x["win_rate"], default=None)
    worst = min(teammates, key=lambda x: x["win_rate"], default=None)

    return PlayerStats(
        games_played=basic.games_played,
        wins=basic.wins,
        win_rate=(basic.wins / basic.games_played) if basic.games_played else 0.0,
        average_team_score=basic.avg_team_score,
        average_opponent_score=basic.avg_opponent_score,
        best_teammate=best,
        worst_teammate=worst,
        **streaks,
    )
