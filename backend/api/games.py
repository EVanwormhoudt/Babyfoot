from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import Session, select

from .db_errors import map_integrity_error
from ..db.models import Game, Team, Player, GamePlayerRatingChange, PlayerRatingHistory
from ..db.session import get_session
from ..ranking import (
    calculate_game_rating_snapshots,
    build_game_rating_change_rows,
    recalculate_all_ratings,
)
from ..schemas import GameCreate, GameRead, GameUpdate, GamesList
from ..settings import settings


router = APIRouter()


def _validate_score_bounds(score_team1: int, score_team2: int) -> None:
    if score_team1 < 0 or score_team2 < 0:
        raise HTTPException(422, "Les scores doivent etre positifs ou nuls")
    if score_team1 > 10 or score_team2 > 10:
        raise HTTPException(422, "Les scores doivent etre compris entre 0 et 10")


def _same_day_base_snapshot(
        session: Session,
        players: list[Player],
        rating_types: list[str],
        day_ts: datetime,
) -> dict[tuple[int, str], dict[str, float]]:
    day_start = day_ts.replace(hour=0, minute=0, second=0, microsecond=0)
    next_day = day_start + timedelta(days=1)
    player_ids = [player.id for player in players]

    delta_rows = session.exec(
        select(
            GamePlayerRatingChange.player_id,
            GamePlayerRatingChange.rating_type,
            func.coalesce(func.sum(GamePlayerRatingChange.delta_mu), 0.0).label("delta_mu"),
        )
        .join(Game, Game.id == GamePlayerRatingChange.game_id)
        .where(
            GamePlayerRatingChange.player_id.in_(player_ids),
            GamePlayerRatingChange.rating_type.in_(rating_types),
            Game.game_timestamp >= day_start,
            Game.game_timestamp < next_day,
        )
        .group_by(GamePlayerRatingChange.player_id, GamePlayerRatingChange.rating_type)
    ).all()

    delta_by_key = {
        (int(row.player_id), str(row.rating_type)): float(row.delta_mu or 0.0)
        for row in delta_rows
    }

    snapshot: dict[tuple[int, str], dict[str, float]] = {}
    for player in players:
        if player.rating is None:
            raise ValueError(f"Player {player.id} is missing a rating row")
        for rating_type in rating_types:
            snapshot[(player.id, rating_type)] = {
                "mu": float(player.rating.get_mu(rating_type)) - delta_by_key.get((player.id, rating_type), 0.0),
                "sigma": float(player.rating.get_sigma(rating_type)),
            }
    return snapshot


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
    _validate_score_bounds(payload.result_team1, payload.result_team2)
    if any(t.team_number not in (1, 2) for t in payload.teams):
        raise HTTPException(422, "team_number doit valoir 1 ou 2")
    if not payload.teams:
        raise HTTPException(422, "Chaque match doit contenir au moins un joueur")

    ids = [t.player_id for t in payload.teams]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Joueurs en double dans les equipes")
    if not any(t.team_number == 1 for t in payload.teams) or not any(t.team_number == 2 for t in payload.teams):
        raise HTTPException(422, "Chaque equipe doit contenir au moins un joueur")

    latest_saved_rating = aliased(PlayerRatingHistory)
    latest_saved_rating_sq = (
        select(
            PlayerRatingHistory.update_id.label("update_id"),
            PlayerRatingHistory.player_id.label("player_id"),
            PlayerRatingHistory.rank_type.label("rank_type"),
            func.row_number().over(
                partition_by=(PlayerRatingHistory.player_id, PlayerRatingHistory.rank_type),
                order_by=(PlayerRatingHistory.date.desc(), PlayerRatingHistory.update_id.desc()),
            ).label("rn"),
        )
        .where(
            PlayerRatingHistory.player_id.in_(ids),
            PlayerRatingHistory.rank_type.in_(("overall", "yearly", "monthly")),
        )
        .subquery()
    )

    rows = session.exec(
        select(Player, latest_saved_rating)
        .where(Player.id.in_(ids))
        .options(selectinload(Player.rating))
        .join(
            latest_saved_rating_sq,
            and_(
                latest_saved_rating_sq.c.player_id == Player.id,
                latest_saved_rating_sq.c.rn == 1,
            ),
            isouter=True,
        )
        .join(
            latest_saved_rating,
            latest_saved_rating.update_id == latest_saved_rating_sq.c.update_id,
            isouter=True,
        )
    ).all()

    players_by_id: dict[int, Player] = {}
    for player, latest_saved_row in rows:
        existing = players_by_id.setdefault(player.id, player)
        latest_saved_ratings = existing.__dict__.setdefault(
            "latest_saved_ratings",
            {
                "overall": None,
                "yearly": None,
                "monthly": None,
            },
        )
        if latest_saved_row is not None:
            latest_saved_ratings[latest_saved_row.rank_type] = latest_saved_row

    players = list(players_by_id.values())
    for player in players:
        latest_saved_ratings = player.__dict__.setdefault(
            "latest_saved_ratings",
            {
                "overall": None,
                "yearly": None,
                "monthly": None,
            },
        )
        # Keep backward compatibility with the previous one-row attribute.
        player.__dict__["latest_saved_rating"] = latest_saved_ratings["overall"]
        player.__dict__["latest_saved_rating_overall"] = latest_saved_ratings["overall"]
        player.__dict__["latest_saved_rating_yearly"] = latest_saved_ratings["yearly"]
        player.__dict__["latest_saved_rating_annual"] = latest_saved_ratings["yearly"]
        player.__dict__["latest_saved_rating_monthly"] = latest_saved_ratings["monthly"]

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
        rating_types = ["overall", "yearly", "monthly"]
        base_snapshot = _same_day_base_snapshot(session, players_in_game, rating_types, now)
        before, after, resolved_rating_types, ts = calculate_game_rating_snapshots(
            new_game,
            team1,
            team2,
            rating_types=rating_types,
            timestamp_tz=settings.tz,
            rating_snapshot=base_snapshot,
        )

        for row in build_game_rating_change_rows(
                new_game.id,
                players_in_game,
                before,
                after,
                resolved_rating_types,
        ):
            session.add(row)

        for player in players_in_game:
            if player.rating is None:
                raise ValueError(f"Player {player.id} is missing a rating row")
            for rating_type in resolved_rating_types:
                key = (player.id, rating_type)
                delta_mu = after[key]["mu"] - before[key]["mu"]
                player.rating.set_mu(rating_type, float(player.rating.get_mu(rating_type)) + delta_mu)
                player.rating.set_sigma(rating_type, after[key]["sigma"])
            player.rating.last_updated = ts

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
    _validate_score_bounds(payload.result_team1, payload.result_team2)

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
