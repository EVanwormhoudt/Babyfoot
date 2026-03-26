from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from .db_errors import map_integrity_error
from ..db.models import Game, Team, Player, GamePlayerRatingChange
from ..db.session import get_session
from ..ranking import (
    recalculate_all_ratings,
    update_all_ratings,
    snapshot_player_ratings,
    build_game_rating_change_rows,
    RATING_TYPES_ALL,
)
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
        raise HTTPException(422, "start_date doit etre <= end_date")

    stmt = (
        select(Game)
        .options(
            selectinload(Game.teams).selectinload(Team.player),
            selectinload(Game.rating_changes),
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
        raise HTTPException(422, "Les scores doivent etre positifs ou nuls")
    if any(t.team_number not in (1, 2) for t in payload.teams):
        raise HTTPException(422, "team_number doit valoir 1 ou 2")
    if not payload.teams:
        raise HTTPException(422, "Chaque match doit contenir au moins un joueur")

    ids = [t.player_id for t in payload.teams]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Joueurs en double dans les equipes")
    if not any(t.team_number == 1 for t in payload.teams) or not any(t.team_number == 2 for t in payload.teams):
        raise HTTPException(422, "Chaque equipe doit contenir au moins un joueur")

    players = session.exec(
        select(Player).where(Player.id.in_(ids)).options(selectinload(Player.rating))
    ).all()
    players_by_id = {p.id: p for p in players}
    missing_ids = sorted(set(ids) - set(players_by_id))
    if missing_ids:
        raise HTTPException(422, f"player_id inconnu(s) : {missing_ids}")

    missing_rating = sorted(p.id for p in players if p.rating is None)
    if missing_rating:
        raise HTTPException(409, f"Ligne de classement manquante pour le(s) joueur(s) : {missing_rating}")

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

        players_in_game = team1 + team2
        before = snapshot_player_ratings(players_in_game, RATING_TYPES_ALL)
        update_all_ratings(new_game, team1, team2)
        after = snapshot_player_ratings(players_in_game, RATING_TYPES_ALL)
        for row in build_game_rating_change_rows(
                new_game.id,
                players_in_game,
                before,
                after,
                RATING_TYPES_ALL,
        ):
            session.add(row)
        session.commit()

        # Eager-load relationships so Pydantic can serialize after the transaction
        game_full = session.exec(
            select(Game)
            .options(selectinload(Game.teams).selectinload(Team.player), selectinload(Game.rating_changes))
            .where(Game.id == new_game.id)
        ).first()
        return game_full
    except HTTPException:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Echec de creation du match (contrainte base de donnees)")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Echec de creation du match : {e}")


@router.get("/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)) -> GameRead:
    game = session.exec(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.teams).selectinload(Team.player), selectinload(Game.rating_changes))
    ).first()
    if not game:
        raise HTTPException(404, "Match introuvable")
    return game


@router.put("/{game_id}", response_model=GameRead)
def update_game(game_id: int, payload: GameUpdate, session: Session = Depends(get_session)):
    g = session.get(Game, game_id)
    if not g:
        raise HTTPException(404, "Match introuvable")
    if payload.result_team1 < 0 or payload.result_team2 < 0:
        raise HTTPException(422, "Les scores doivent etre positifs ou nuls")

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
        raise map_integrity_error(e, "Echec de mise a jour du match (contrainte base de donnees)")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Echec de mise a jour du match : {e}")

    updated = session.exec(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.teams).selectinload(Team.player), selectinload(Game.rating_changes))
    ).first()
    return updated


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, session: Session = Depends(get_session)):
    g = session.exec(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.teams), selectinload(Game.rating_changes))
    ).first()
    if not g:
        raise HTTPException(404, "Match introuvable")

    # Fast path: when deleting the latest game, restore impacted players from
    # the stored per-game snapshots and avoid a full replay of history.
    if g.rating_changes:
        if g.game_timestamp is None:
            newer_exists = session.exec(
                select(Game.id).where(Game.id > g.id).limit(1)
            ).first() is not None
        else:
            newer_exists = session.exec(
                select(Game.id).where(
                    or_(
                        Game.game_timestamp > g.game_timestamp,
                        and_(Game.game_timestamp == g.game_timestamp, Game.id > g.id),
                    )
                ).limit(1)
            ).first() is not None

        if not newer_exists:
            player_ids = sorted({row.player_id for row in g.rating_changes})
            players = session.exec(
                select(Player)
                .where(Player.id.in_(player_ids))
                .options(selectinload(Player.rating))
            ).all()
            players_by_id = {p.id: p for p in players}

            if all(players_by_id.get(pid) and players_by_id[pid].rating for pid in player_ids):
                now = datetime.now(tz=settings.tz)
                try:
                    for row in g.rating_changes:
                        player = players_by_id[row.player_id]
                        player.rating.set_mu(row.rating_type, row.mu_before)
                        player.rating.set_sigma(row.rating_type, row.sigma_before)
                        player.rating.last_updated = now

                    for row in g.rating_changes:
                        session.delete(row)
                    for team in g.teams:
                        session.delete(team)
                    session.delete(g)
                    session.commit()
                    return None
                except IntegrityError as e:
                    session.rollback()
                    raise map_integrity_error(e, "Echec de suppression du match (contrainte base de donnees)")
                except Exception as e:
                    session.rollback()
                    raise HTTPException(500, f"Echec de suppression du match : {e}")

    try:
        rating_changes = session.exec(
            select(GamePlayerRatingChange).where(GamePlayerRatingChange.game_id == game_id)
        ).all()
        for row in rating_changes:
            session.delete(row)

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
        raise map_integrity_error(e, "Echec de suppression du match (contrainte base de donnees)")
    except Exception as e:
        session.rollback()
        raise HTTPException(500, f"Echec de suppression du match : {e}")

    return None
