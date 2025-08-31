from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..consts import DEFAULT_RATING, DEFAULT_SIGMA
from ..db.models import Player, CurrentPlayerRank
from ..db.session import get_session
from ..schemas import PlayerCreate, PlayerRead, PlayerUpdate
from ..settings import settings

router = APIRouter()


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


@router.get("/leaderboard", response_model=List[PlayerRead])
def get_leaderboard(
        leaderboard_type: Literal["monthly", "yearly", "overall"] = "monthly",
        session: Session = Depends(get_session),
):
    players = session.exec(
        select(Player).where(Player.active == True).options(selectinload(Player.rating))
    ).all()
    players.sort(
        key=lambda x: getattr(x.rating, f"mu_{leaderboard_type}") if x.rating else 0.0,
        reverse=True,
    )
    return players
