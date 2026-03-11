from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from .db_errors import map_integrity_error
from ..db.models import Game, Team, Player
from ..db.session import get_session
from ..ranking import recalculate_all_ratings, update_all_ratings
from ..schemas import GameCreate, GameRead, GameUpdate, GamesList
from ..settings import settings


router = APIRouter()


@router.get("", response_model=GamesList)
def get_games(
        session: Session = Depends(get_session),
        scope: Literal["all", "monthly"] = Query("all"),
        limit: int = Query(10, ge=1, le=200),
        offset: int = Query(0, ge=0),
        start_date: Optional[datetime] = Query(None, description="Filter games starting from this date"),
        end_date: Optional[datetime] = Query(None, description="Filter games up to this date"),
) -> GamesList:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "start_date must be <= end_date")

    stmt = (
        select(Game)
        .options(
            selectinload(Game.teams).selectinload(Team.player)  # load players for each team
        )
    )

    if scope == "monthly":
        first_of_month = datetime.now(tz=settings.tz).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        stmt = stmt.where(Game.game_timestamp >= first_of_month)

    if start_date:
        stmt = stmt.where(Game.game_timestamp >= start_date)
    if end_date:
        stmt = stmt.where(Game.game_timestamp <= end_date)

    stmt = stmt.order_by(Game.game_timestamp.desc()).offset(offset).limit(limit)
    games = session.exec(stmt).all()

    count_stmt = select(func.count()).select_from(Game)
    if scope == "monthly":
        first_of_month = datetime.now(tz=settings.tz).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        count_stmt = count_stmt.where(Game.game_timestamp >= first_of_month)
    if start_date:
        count_stmt = count_stmt.where(Game.game_timestamp >= start_date)
    if end_date:
        count_stmt = count_stmt.where(Game.game_timestamp <= end_date)
    total_games = session.exec(count_stmt).one()
    return {"items": games, "total": total_games}


def _validate_game_payload(payload: GameCreate, session: Session) -> Dict[int, Player]:
    if payload.result_team1 < 0 or payload.result_team2 < 0:
        raise HTTPException(422, "Scores must be non-negative")
    if any(t.team_number not in (1, 2) for t in payload.teams):
        raise HTTPException(422, "team_number must be 1 or 2")
    if not payload.teams:
        raise HTTPException(422, "At least one player per game is required")

    ids = [t.player_id for t in payload.teams]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate players in teams")
    if not any(t.team_number == 1 for t in payload.teams) or not any(t.team_number == 2 for t in payload.teams):
        raise HTTPException(422, "Both teams must have at least one player")

    players = session.exec(
        select(Player).where(Player.id.in_(ids)).options(selectinload(Player.rating))
    ).all()
    players_by_id = {p.id: p for p in players}
    missing_ids = sorted(set(ids) - set(players_by_id))
    if missing_ids:
        raise HTTPException(422, f"Unknown player_id(s): {missing_ids}")

    missing_rating = sorted(p.id for p in players if p.rating is None)
    if missing_rating:
        raise HTTPException(409, f"Player(s) missing rating row: {missing_rating}")

    return players_by_id


@router.post("", response_model=GameRead, status_code=201)
def create_game(game: GameCreate, session: Session = Depends(get_session)):
    players_by_id = _validate_game_payload(game, session)

    now = datetime.now(tz=settings.tz)

    try:
        new_game = Game(
            game_timestamp=now,
            result_team1=game.result_team1,
            result_team2=game.result_team2,
        )
        session.add(new_game)
        session.flush()  # get new_game.id

        for t in game.teams:
            session.add(Team(player_id=t.player_id, team_number=t.team_number, game_id=new_game.id))

        team1 = [players_by_id[t.player_id] for t in game.teams if t.team_number == 1]
        team2 = [players_by_id[t.player_id] for t in game.teams if t.team_number == 2]

        update_all_ratings(new_game, team1, team2)
        session.commit()

        # Eager-load relationships so Pydantic can serialize after the transaction
        game_full = session.exec(
            select(Game)
            .options(selectinload(Game.teams).selectinload(Team.player))
            .where(Game.id == new_game.id)
        ).first()
        return game_full
    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Failed to create game due to a database constraint")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Failed to create game: {e}")


@router.get("/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)) -> GameRead:
    game = session.exec(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.teams).selectinload(Team.player))
    ).first()
    if not game:
        raise HTTPException(404, "Game not found")
    return game


@router.put("/{game_id}", response_model=GameRead)
def update_game(game_id: int, payload: GameUpdate, session: Session = Depends(get_session)):
    g = session.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Game not found")
    if payload.result_team1 < 0 or payload.result_team2 < 0:
        raise HTTPException(422, "Scores must be non-negative")

    try:
        g.result_team1 = payload.result_team1
        g.result_team2 = payload.result_team2
        session.flush()
        recalculate_all_ratings(session)
        session.commit()
    except ValueError as e:
        session.rollback()
        raise HTTPException(409, str(e))
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Failed to update game due to a database constraint")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Failed to update game: {e}")

    updated = session.exec(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.teams).selectinload(Team.player))
    ).first()
    return updated


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, session: Session = Depends(get_session)):
    g = session.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Game not found")
    try:
        teams = session.exec(select(Team).where(Team.game_id == game_id)).all()
        for team in teams:
            session.delete(team)
        session.delete(g)
        session.flush()
        recalculate_all_ratings(session)
        session.commit()
    except ValueError as e:
        session.rollback()
        raise HTTPException(409, str(e))
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Failed to delete game due to a database constraint")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Failed to delete game: {e}")

    return None
