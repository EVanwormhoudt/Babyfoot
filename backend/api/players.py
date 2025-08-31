from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional,Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from sqlalchemy import func, case, and_

from ..consts import DEFAULT_RATING, DEFAULT_SIGMA
from ..db.models import Player, CurrentPlayerRank, Team, Game
from ..db.session import get_session
from ..schemas import PlayerCreate, PlayerRead, PlayerUpdate, PlayerLeaderboard
from ..settings import settings

router = APIRouter()


@router.get("/leaderboard", response_model=List[PlayerLeaderboard])
def get_leaderboard(
        leaderboard_type: Literal["monthly", "yearly", "overall"] = "monthly",
        session: Session = Depends(get_session),
):
    # 1) Figure out the time window
    start_dt, end_dt = period_bounds(leaderboard_type)

    # 2) Build win/loss CASE expressions
    win_case = case(
        (and_(Team.team_number == 1, Game.result_team1 > Game.result_team2), 1),
        (and_(Team.team_number == 2, Game.result_team2 > Game.result_team1), 1),
        else_=0,
    )
    loss_case = case(
        (and_(Team.team_number == 1, Game.result_team1 < Game.result_team2), 1),
        (and_(Team.team_number == 2, Game.result_team2 < Game.result_team1), 1),
        else_=0,
    )
    # If you want draws:
    # draw_case = case(
    #     (Game.result_team1 == Game.result_team2, 1),
    #     else_=0,
    # )

    # 3) Aggregate wins/losses per player in the selected period
    stats_stmt = (
        select(
            Team.player_id.label("player_id"),
            func.coalesce(func.sum(win_case), 0).label("wins"),
            func.coalesce(func.sum(loss_case), 0).label("losses"),
            # func.coalesce(func.sum(draw_case), 0).label("draws"),
        )
        .join(Game, Game.id == Team.game_id)
    )
    if start_dt is not None and end_dt is not None:
        stats_stmt = stats_stmt.where(
            Game.game_timestamp >= start_dt,
            Game.game_timestamp < end_dt,
            )
    stats_stmt = stats_stmt.group_by(Team.player_id)

    stats_rows = session.exec(stats_stmt).all()
    per_player_stats: Dict[int, dict] = {
        r.player_id: {"wins": r.wins or 0, "losses": r.losses or 0} for r in stats_rows
    }

    # 4) Load active players with their current rating
    players = session.exec(
        select(Player)
        .where(Player.active == True)
        .options(selectinload(Player.rating))
    ).all()

    # 5) Sort by the requested rating (fallback 0.0 if missing)
    players.sort(
        key=lambda x: getattr(x.rating, f"mu_{leaderboard_type}") if x.rating else 0.0,
        reverse=True,
    )

    # 6) Build response rows with wins/losses injected
    result: List[PlayerLeaderboard] = []
    for p in players:
        stats = per_player_stats.get(p.id, {"wins": 0, "losses": 0})
        result.append(
            PlayerLeaderboard(
                **p.model_dump(),
                rating=p.rating,
                wins=stats.get("wins", 0),
                games_played=stats.get("wins", 0) + stats.get("losses", 0),
            )
        )


    return result

@router.post("", response_model=PlayerRead, status_code=201)
def create_player(payload: PlayerCreate, session: Session = Depends(get_session)):
    exists = session.exec(select(Player).where(Player.player_name == payload.player_name)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Player already exists")

    p = Player(active=True, **payload.model_dump())
    session.add(p)
    session.commit()
    session.refresh(p)

    p.rating = CurrentPlayerRank(
        player_id=p.id,
        mu_overall=DEFAULT_RATING,
        sigma_overall=DEFAULT_SIGMA,
        mu_monthly=DEFAULT_RATING,
        sigma_monthly=DEFAULT_SIGMA,
        mu_yearly=DEFAULT_RATING,
        sigma_yearly=DEFAULT_SIGMA,
        last_updated=datetime.now(tz=settings.tz),
    )
    session.add(p.rating)
    session.commit()
    session.refresh(p)
    return p


@router.get("", response_model=List[PlayerRead])
def list_players(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session),
):
    q = (
        select(Player)
        .options(selectinload(Player.rating))
        .offset(offset)
        .limit(limit)
    )
    return session.exec(q).all()


@router.get("/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, session: Session = Depends(get_session)):
    player = session.exec(
        select(Player).where(Player.id == player_id).options(selectinload(Player.rating))
    ).first()
    if not player:
        raise HTTPException(404, "Player not found")
    return player


@router.put("/{player_id}", response_model=PlayerRead)
def update_player(player_id: int, payload: PlayerUpdate, session: Session = Depends(get_session)):
    p = session.get(Player, player_id)
    if not p:
        raise HTTPException(404, "Player not found")
    for k, v in payload.model_dump().items():
        setattr(p, k, v)
    session.commit()
    session.refresh(p)
    return p


@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: int, session: Session = Depends(get_session)):
    p = session.get(Player, player_id)
    if not p:
        raise HTTPException(404, "Player not found")
    session.delete(p)
    session.commit()
    return None




def period_bounds(leaderboard_type: str) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    now = datetime.now()
    if leaderboard_type == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # first day of next month
        if start.month == 12:
            end = start.replace(year=start.year+1, month=1)
        else:
            end = start.replace(month=start.month+1)
        return start, end
    if leaderboard_type == "yearly":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year+1)
        return start, end
    # overall: no bounds
    return None, None