from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from sqlalchemy import func, case, and_
from sqlalchemy.exc import IntegrityError

from .db_errors import map_integrity_error
from ..consts import DEFAULT_RATING, DEFAULT_SIGMA
from ..db.models import Player, CurrentPlayerRank, Team, Game, PlayerRatingHistory
from ..db.session import get_session
from ..schemas import (
    PlayerCreate,
    PlayerRead,
    PlayerUpdate,
    PlayerLeaderboard,
    PlayerRatingHistoryPoint,
)
from ..settings import settings

router = APIRouter()


@router.get("/leaderboard", response_model=List[PlayerLeaderboard])
def get_leaderboard(
        leaderboard_type: Literal["monthly", "yearly", "overall"] = Query("monthly"),
        year: Optional[int] = Query(
            None,
            description="Year to filter by (used for 'monthly' and 'yearly'). Defaults to current year.",
        ),
        month: Optional[int] = Query(
            None,
            ge=1,
            le=12,
            description="Month (1..12). Only used for 'monthly'. Defaults to current month.",
        ),
        session: Session = Depends(get_session),
):
    from sqlalchemy.orm import aliased  # local import so you don't need to modify globals

    # 1) Figure out the time window (using provided year/month if applicable)
    try:
        start_dt, end_dt = period_bounds(leaderboard_type, year=year, month=month)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

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

    # 3) Aggregate wins/losses per player in the selected period
    stats_stmt = (
        select(
            Team.player_id.label("player_id"),
            func.coalesce(func.sum(win_case), 0).label("wins"),
            func.coalesce(func.sum(loss_case), 0).label("losses"),
        )
        .select_from(Team)
        .join(Game, Game.id == Team.game_id)
    )

    if start_dt is not None and end_dt is not None:
        # end is exclusive
        stats_stmt = stats_stmt.where(
            Game.game_timestamp >= start_dt,
            Game.game_timestamp < end_dt,
            )

    stats_stmt = stats_stmt.group_by(Team.player_id)
    stats_rows = session.exec(stats_stmt).all()
    per_player_stats: Dict[int, dict] = {
        r.player_id: {"wins": int(r.wins or 0), "losses": int(r.losses or 0)} for r in stats_rows
    }

    # 4) Load players with the correct rating snapshot
    use_live = is_current_period(leaderboard_type, start_dt, end_dt)

    if use_live or leaderboard_type == "overall":
        # Live / overall: use CurrentPlayerRank relationship
        players_live: List[Player] = session.exec(
            select(Player)
            .where(Player.active == True)
            .options(selectinload(Player.rating))
        ).all()
        rows = [(p, None) for p in players_live]  # normalize shape to (Player, hist)
    else:
        # Historical snapshot: pick the latest PlayerRatingHistory *within [start_dt, end_dt)*
        PH = aliased(PlayerRatingHistory)
        ph_sub = (
            select(
                PlayerRatingHistory.player_id.label("player_id"),
                func.max(PlayerRatingHistory.date).label("last_ts"),
            )
            .where(
                PlayerRatingHistory.rank_type == leaderboard_type,
                PlayerRatingHistory.date >= start_dt,
                PlayerRatingHistory.date < end_dt,  # end exclusive
            )
            .group_by(PlayerRatingHistory.player_id)
            .subquery()
        )

        rows = session.exec(
            select(Player, PH)
            .join(ph_sub, ph_sub.c.player_id == Player.id, isouter=True)
            .join(
                PH,
                and_(
                    PH.player_id == Player.id,
                    PH.date == ph_sub.c.last_ts,
                    PH.rank_type == leaderboard_type,
                    ),
                isouter=True,
            )
            .where(Player.active == True)
        ).all()  # rows: List[Tuple[Player, PlayerRatingHistory|None]]

    # 5) Helpers to compute mu and sort
    def mu_for(row) -> float:
        p, hist = row
        if use_live or leaderboard_type == "overall":
            return getattr(p.rating, f"mu_{leaderboard_type}", 0.0) if p.rating else 0.0
        else:
            return float(hist.mu) if hist and hist.mu is not None else 0.0

    def wins_for(player_id: int) -> int:
        return per_player_stats.get(player_id, {}).get("wins", 0)

    # Sort by rating desc, then wins desc, then player_id asc for stability
    rows.sort(key=lambda r: (mu_for(r), wins_for(r[0].id), -r[0].id), reverse=True)

    # 6) Build response rows with wins/losses injected
    result: List[PlayerLeaderboard] = []
    for p, hist in rows:
        stats = per_player_stats.get(p.id, {"wins": 0, "losses": 0})
        mu_val = mu_for((p, hist))
        result.append(
            PlayerLeaderboard(
                **p.model_dump(),
                rating=p.rating if (use_live or leaderboard_type == "overall") else None,
                mu=mu_val,
                wins=stats["wins"],
                games_played=stats["wins"] + stats["losses"],
                # losses=stats["losses"],  # include if your schema supports it
            )
        )

    return result



@router.post("", response_model=PlayerRead, status_code=201)
def create_player(payload: PlayerCreate, session: Session = Depends(get_session)):
    exists = session.exec(select(Player).where(Player.player_name == payload.player_name)).first()
    if exists:
        raise HTTPException(status_code=400, detail="Le joueur existe deja")

    try:
        p = Player(active=True, **payload.model_dump())
        session.add(p)
        session.flush()

        session.add(
            CurrentPlayerRank(
                player_id=p.id,
                mu_overall=DEFAULT_RATING,
                sigma_overall=DEFAULT_SIGMA,
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                mu_yearly=DEFAULT_RATING,
                sigma_yearly=DEFAULT_SIGMA,
                last_updated=datetime.now(tz=settings.tz),
            )
        )
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Echec de creation du joueur (contrainte base de donnees)")
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Echec de creation du joueur : {e}")

    created = session.exec(
        select(Player)
        .where(Player.id == p.id)
        .options(selectinload(Player.rating))
    ).first()
    return created


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
        raise HTTPException(404, "Joueur introuvable")
    return player


@router.get("/{player_id}/rating-history", response_model=List[PlayerRatingHistoryPoint])
def get_player_rating_history(
        player_id: int,
        rating_type: Optional[Literal["monthly", "yearly", "overall"]] = Query(
            None,
            description="Optional filter for rating snapshot type",
        ),
        session: Session = Depends(get_session),
):
    if not session.get(Player, player_id):
        raise HTTPException(404, "Joueur introuvable")

    stmt = (
        select(PlayerRatingHistory)
        .where(PlayerRatingHistory.player_id == player_id)
        .order_by(PlayerRatingHistory.date.asc(), PlayerRatingHistory.update_id.asc())
    )
    if rating_type is not None:
        stmt = stmt.where(PlayerRatingHistory.rank_type == rating_type)

    return session.exec(stmt).all()


@router.put("/{player_id}", response_model=PlayerRead)
def update_player(player_id: int, payload: PlayerUpdate, session: Session = Depends(get_session)):
    p = session.get(Player, player_id)
    if not p:
        raise HTTPException(404, "Joueur introuvable")
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)

    if "player_name" in updates and updates["player_name"] != p.player_name:
        exists = session.exec(
            select(Player).where(Player.player_name == updates["player_name"], Player.id != player_id)
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="Le joueur existe deja")

    for k, v in updates.items():
        setattr(p, k, v)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Echec de mise a jour du joueur (contrainte base de donnees)")

    updated = session.exec(
        select(Player).where(Player.id == player_id).options(selectinload(Player.rating))
    ).first()
    return updated


@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: int, session: Session = Depends(get_session)):
    p = session.get(Player, player_id)
    if not p:
        raise HTTPException(404, "Joueur introuvable")

    has_games = session.exec(
        select(Team.id).where(Team.player_id == player_id).limit(1)
    ).first()
    if has_games:
        raise HTTPException(409, "Impossible de supprimer un joueur avec historique de matchs ; desactivez-le plutot")

    rank = session.get(CurrentPlayerRank, player_id)
    if rank:
        session.delete(rank)

    history_rows = session.exec(
        select(PlayerRatingHistory).where(PlayerRatingHistory.player_id == player_id)
    ).all()
    for row in history_rows:
        session.delete(row)

    session.delete(p)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise map_integrity_error(e, "Echec de suppression du joueur (contrainte base de donnees)")

    return None


def period_bounds(
        leaderboard_type: Literal["monthly", "yearly", "overall"],
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Returns [start, end) bounds (end exclusive) for the requested period.
    - overall: (None, None)
    - yearly: [Jan 1 yyyy, Jan 1 yyyy+1)
    - monthly: [1st of (yyyy, mm), 1st of next month)
    Defaults: current year/month if not provided.
    """
    tzinfo = settings.tz
    if leaderboard_type == "overall":
        return None, None

    now = datetime.now(tz=settings.tz)
    y = year or now.year

    if leaderboard_type == "yearly":
        start = datetime(y, 1, 1, tzinfo=tzinfo)
        end = datetime(y + 1, 1, 1, tzinfo=tzinfo)
        return start, end

    # monthly
    m = month or now.month
    if not 1 <= m <= 12:
        raise ValueError("month doit etre entre 1 et 12")

    start = datetime(y, m, 1, tzinfo=tzinfo)
    if m == 12:
        end = datetime(y + 1, 1, 1, tzinfo=tzinfo)
    else:
        end = datetime(y, m + 1, 1, tzinfo=tzinfo)
    return start, end

def is_current_period(
        leaderboard_type: Literal["monthly", "yearly", "overall"],
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
) -> bool:
    if leaderboard_type == "overall":
        return True
    now = datetime.now(tz=settings.tz)
    return (start_dt is not None) and (end_dt is not None) and (start_dt <= now < end_dt)
