import datetime
from typing import Optional

from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from backend.db.models import Game, Team, Player
from backend.settings import settings
from sqlalchemy import case, and_, or_, func


def get_scope_bounds(
        scope: str,
        year: Optional[int] = None,
        month: Optional[int] = None,
) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    now = datetime.datetime.now(tz=settings.tz)
    if scope == "overall":
        return None, None

    y = year or now.year
    if scope == "yearly":
        start = datetime.datetime(y, 1, 1, tzinfo=settings.tz)
        end = datetime.datetime(y + 1, 1, 1, tzinfo=settings.tz)
        return start, end

    if scope == "monthly":
        m = month or now.month
        if not 1 <= m <= 12:
            raise ValueError("month must be in 1..12")
        start = datetime.datetime(y, m, 1, tzinfo=settings.tz)
        if m == 12:
            end = datetime.datetime(y + 1, 1, 1, tzinfo=settings.tz)
        else:
            end = datetime.datetime(y, m + 1, 1, tzinfo=settings.tz)
        return start, end

    raise ValueError("scope must be one of: overall, monthly, yearly")


def get_win_streaks(
        session: Session,
        player_id: int,
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
):
    stmt = (
        select(Game, Team)
        .join(Team, Game.id == Team.game_id)
        .where(Team.player_id == player_id)
        .order_by(Game.game_timestamp)
    )
    if start_date:
        stmt = stmt.where(Game.game_timestamp >= start_date)
    if end_date:
        stmt = stmt.where(Game.game_timestamp < end_date)

    results = session.exec(stmt).all()

    streak = 0
    max_streak = 0

    for game, team in results:
        won = (
                (team.team_number == 1 and game.result_team1 > game.result_team2)
                or (team.team_number == 2 and game.result_team2 > game.result_team1)
        )
        if won:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {"longest_win_streak": max_streak, "current_win_streak": streak}


def get_basic_stats(
        session: Session,
        player_id: int,
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
):
    team_alias = Team
    game_alias = Game

    stmt = (
        select(
            func.count().label("games_played"),
            func.sum(
                case(
                    (
                        or_(
                            and_(team_alias.team_number == 1, game_alias.result_team1 > game_alias.result_team2),
                            and_(team_alias.team_number == 2, game_alias.result_team2 > game_alias.result_team1),
                        ),
                        1
                    ),
                    else_=0
                )
            ).label("wins"),
            func.avg(
                case(
                    (team_alias.team_number == 1, game_alias.result_team1),
                    else_=game_alias.result_team2
                )
            ).label("avg_team_score"),
            func.avg(
                case(
                    (team_alias.team_number == 1, game_alias.result_team2),
                    else_=game_alias.result_team1
                )
            ).label("avg_opponent_score")
        )
        .join(game_alias, game_alias.id == team_alias.game_id)
        .where(team_alias.player_id == player_id)
    )

    if start_date:
        stmt = stmt.where(game_alias.game_timestamp >= start_date)
    if end_date:
        stmt = stmt.where(game_alias.game_timestamp < end_date)

    return session.exec(stmt).one()


def get_teammate_stats(
        session: Session,
        player_id: int,
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
):
    PT = Team  # player_team alias
    T = aliased(Team, name="teammate")  # teammate alias
    P = Player
    G = Game

    # Join structure:
    stmt = (
        select(
            T.player_id,
            P.player_name,
            func.count().label("games_played"),
            func.sum(
                case(
                    (
                        or_(
                            and_(T.team_number == 1, G.result_team1 > G.result_team2),
                            and_(T.team_number == 2, G.result_team2 > G.result_team1)
                        ),
                        1
                    ),
                    else_=0
                )
            ).label("wins")
        )
        .select_from(PT)
        .join(T, and_(
            T.game_id == PT.game_id,
            T.team_number == PT.team_number,
            T.player_id != PT.player_id
        ))
        .join(P, and_(P.id == T.player_id, P.active == True))
        .join(G, G.id == PT.game_id)
        .where(PT.player_id == player_id)
        .group_by(T.player_id, P.player_name)
        .having(func.count() >= 3)
    )

    if start_date:
        stmt = stmt.where(G.game_timestamp >= start_date)
    if end_date:
        stmt = stmt.where(G.game_timestamp < end_date)

    rows = session.exec(stmt).all()

    return [
        {
            "player_id": row[0],
            "player_name": row[1],
            "games_played": row[2],
            "wins": row[3],
            "win_rate": row[3] / row[2] if row[2] else 0
        }
        for row in rows
    ]
