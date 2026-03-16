from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db.models import Game, Player, Team
from ..db.session import get_session
from ..schemas import GameRead, PlayerStats
from ..utils import get_scope_bounds, get_basic_stats, get_teammate_stats, get_win_streaks

router = APIRouter()


@router.get("/{player_id}/history", response_model=List[GameRead])
def get_player_games(player_id: int, session: Session = Depends(get_session)):
    if not session.get(Player, player_id):
        raise HTTPException(404, "Joueur introuvable")
    games = session.exec(
        select(Game)
        .options(selectinload(Game.teams).selectinload(Team.player))
        .join(Team, Team.game_id == Game.id)
        .where(Team.player_id == player_id)
        .order_by(Game.game_timestamp.desc())
    ).all()
    return games


@router.get("/{player_id}/stats", response_model=PlayerStats)
def get_player_stats(
        player_id: int,
        scope: Literal["overall", "monthly", "yearly"] = Query("overall"),
        year: int | None = Query(
            None,
            description="Year to filter by (used for monthly/yearly). Defaults to current year.",
        ),
        month: int | None = Query(
            None,
            ge=1,
            le=12,
            description="Month (1..12). Used only for monthly. Defaults to current month.",
        ),
        session: Session = Depends(get_session),
):
    if not session.get(Player, player_id):
        raise HTTPException(404, "Joueur introuvable")

    if scope != "monthly" and month is not None:
        raise HTTPException(422, "month est supporte uniquement quand scope=monthly")

    try:
        start_dt, end_dt = get_scope_bounds(scope, year=year, month=month)
    except ValueError as e:
        raise HTTPException(422, str(e))

    basic = get_basic_stats(session, player_id, start_dt, end_dt)
    teammates = get_teammate_stats(session, player_id, start_dt, end_dt)
    streaks = get_win_streaks(session, player_id, start_dt, end_dt)

    games_played = int(basic.games_played or 0)
    wins = int(basic.wins or 0)
    average_team_score = float(basic.avg_team_score or 0.0)
    average_opponent_score = float(basic.avg_opponent_score or 0.0)

    best = max(teammates, key=lambda x: x["win_rate"], default=None)
    worst = min(teammates, key=lambda x: x["win_rate"], default=None)

    return PlayerStats(
        games_played=games_played,
        wins=wins,
        win_rate=(wins / games_played) if games_played else 0.0,
        average_team_score=average_team_score,
        average_opponent_score=average_opponent_score,
        best_teammate=best,
        worst_teammate=worst,
        **streaks,
    )
