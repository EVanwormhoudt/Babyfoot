from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db.models import Game, Team, Player
from ..db.session import get_session
from ..ranking import update_all_ratings
from ..schemas import GameCreate, GameRead, GameUpdate
from ..settings import settings

router = APIRouter()


@router.get("", response_model=List[GameRead])
def get_games(
        session: Session = Depends(get_session),
        scope: Optional[str] = Query("all", enum=["all", "monthly"]),
        limit: int = Query(10, ge=1, le=200),
        offset: int = Query(0, ge=0),
) -> List[GameRead]:
    stmt = select(Game).options(selectinload(Game.teams))

    if scope == "monthly":
        now = settings.tz
        # first day of month at midnight
        from datetime import datetime
        first_of_month = datetime.now(tz=settings.tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(Game.game_timestamp >= first_of_month)

    stmt = stmt.order_by(Game.game_timestamp.desc()).offset(offset).limit(limit)
    games = session.exec(stmt).all()
    return games


def _validate_game_payload(payload: GameCreate):
    if payload.result_team1 < 0 or payload.result_team2 < 0:
        raise HTTPException(422, "Scores must be non-negative")
    if any(t.team_number not in (1, 2) for t in payload.teams):
        raise HTTPException(422, "team_number must be 1 or 2")
    ids = [t.player_id for t in payload.teams]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate players in teams")
    if not any(t.team_number == 1 for t in payload.teams) or not any(t.team_number == 2 for t in payload.teams):
        raise HTTPException(422, "Both teams must have at least one player")


@router.post("", response_model=GameRead, status_code=201)
def create_game(game: GameCreate, session: Session = Depends(get_session)):
    from datetime import datetime

    _validate_game_payload(game)

    now = datetime.now(tz=settings.tz)

    # transactional pattern: use a transaction without closing the session
    try:
        with session.begin():
            new_game = Game(
                game_timestamp=now,
                result_team1=game.result_team1,
                result_team2=game.result_team2,
            )
            session.add(new_game)
            session.flush()  # get new_game.id

            for t in game.teams:
                session.add(Team(player_id=t.player_id, team_number=t.team_number, game_id=new_game.id))

            # fetch players with ratings for both teams
            players = session.exec(
                select(Player)
                .join(Team, Team.player_id == Player.id)
                .where(Team.game_id == new_game.id)
                .options(selectinload(Player.rating))
            ).all()

            team1 = [p for p in players if any(tm.player_id == p.id and tm.team_number == 1 for tm in game.teams)]
            team2 = [p for p in players if any(tm.player_id == p.id and tm.team_number == 2 for tm in game.teams)]

            if not team1 or not team2:
                raise HTTPException(400, "Both teams must have players")

            update_all_ratings(new_game, team1, team2)

            session.refresh(new_game)
            # Eager-load relationships so Pydantic can serialize after the transaction
            game_full = session.exec(
                select(Game)
                .options(selectinload(Game.teams))
                .where(Game.id == new_game.id)
            ).first()
            return game_full
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create game: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create game: {e}")


@router.get("/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)) -> GameRead:
    game = session.exec(
        select(Game).where(Game.id == game_id).options(selectinload(Game.teams))
    ).first()
    if not game:
        raise HTTPException(404, "Game not found")
    return game


@router.put("/{game_id}", response_model=GameRead)
def update_game(game_id: int, payload: GameUpdate, session: Session = Depends(get_session)):
    g = session.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Game not found")
    for k, v in payload.model_dump().items():
        setattr(g, k, v)
    session.commit()
    session.refresh(g)
    return g


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, session: Session = Depends(get_session)):
    g = session.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Game not found")
    session.delete(g)
    session.commit()
    return None
