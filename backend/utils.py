import datetime
from typing import Optional

from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from backend.db.models import Game, Team, Player
from sqlalchemy import case, and_, or_, func


def get_scope_date(scope: str) -> Optional[datetime.datetime]:
    now = datetime.datetime.now(datetime.UTC)
    if scope == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif scope == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return None  # overall


def get_win_streaks(session: Session, player_id: int, date_filter: Optional[datetime]):
    stmt = (
        select(Game, Team)
        .join(Team, Game.id == Team.game_id)
        .where(Team.player_id == player_id)
        .order_by(Game.game_timestamp)
    )
    if date_filter:
        stmt = stmt.where(Game.game_timestamp >= date_filter)

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


def get_basic_stats(session: Session, player_id: int, date_filter: Optional[datetime]):
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

    if date_filter:
        stmt = stmt.where(game_alias.game_timestamp >= date_filter)

    result = session.exec(stmt).one()

    return result


def get_teammate_stats(session: Session, player_id: int, date_filter: Optional[datetime]):
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

    if date_filter:
        stmt = stmt.where(G.game_timestamp >= date_filter)

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
