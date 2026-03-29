import datetime as _dt
from typing import Any, Callable, Dict, List, Optional, Sequence, TYPE_CHECKING

from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..consts import DEFAULT_RATING, DEFAULT_SIGMA
from ..db.models import CurrentPlayerRank, Game, GamePlayerRatingChange, Player, Team
from ..settings import settings

if TYPE_CHECKING:
    from sqlmodel import Session

RATING_TYPES_ALL = ["overall", "monthly", "yearly"]


def snapshot_player_ratings(
        players: Sequence["Player"],
        rating_types: Sequence[str],
) -> Dict[tuple[int, str], Dict[str, float]]:
    snapshot: Dict[tuple[int, str], Dict[str, float]] = {}
    for player in players:
        if player.rating is None:
            raise ValueError(f"Player {player.id} is missing a rating row")
        for rating_type in rating_types:
            snapshot[(player.id, rating_type)] = {
                "mu": float(player.rating.get_mu(rating_type)),
                "sigma": float(player.rating.get_sigma(rating_type)),
            }
    return snapshot


def build_game_rating_change_rows(
        game_id: int,
        players: Sequence["Player"],
        before: Dict[tuple[int, str], Dict[str, float]],
        after: Dict[tuple[int, str], Dict[str, float]],
        rating_types: Sequence[str],
) -> List[GamePlayerRatingChange]:
    rows: List[GamePlayerRatingChange] = []
    for player in players:
        for rating_type in rating_types:
            before_key = before[(player.id, rating_type)]
            after_key = after[(player.id, rating_type)]
            rows.append(
                GamePlayerRatingChange(
                    game_id=game_id,
                    player_id=player.id,
                    rating_type=rating_type,
                    mu_before=before_key["mu"],
                    mu_after=after_key["mu"],
                    sigma_before=before_key["sigma"],
                    sigma_after=after_key["sigma"],
                    delta_mu=after_key["mu"] - before_key["mu"],
                )
            )
    return rows


def _normalize_ts(
        ts: Optional[_dt.datetime],
        tz: _dt.tzinfo,
) -> Optional[_dt.datetime]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=tz)
    return ts.astimezone(tz)


def _period_starts(now: _dt.datetime) -> tuple[_dt.datetime, _dt.datetime]:
    first_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return first_of_year, first_of_month


def _rating_types_for_game(
        game_ts: Optional[_dt.datetime],
        first_of_year: _dt.datetime,
        first_of_month: _dt.datetime,
) -> List[str]:
    rating_types = ["overall"]
    if game_ts is not None and game_ts >= first_of_year:
        rating_types.append("yearly")
    if game_ts is not None and game_ts >= first_of_month:
        rating_types.append("monthly")
    return rating_types


def _mov_multiplier(
        score1: float,
        score2: float,
        *,
        mov_top: float = 1.25,
        max_margin: float = 10.0,
) -> float:
    """
    Mild margin-of-victory scaling for foosball.

    Examples with mov_top=1.25:
      10-9 -> 1.025
      10-5 -> 1.125
      10-0 -> 1.25
    """
    margin = min(max_margin, abs(float(score1) - float(score2)))
    return 1.0 + (mov_top - 1.0) * (margin / max_margin)


def update_all_ratings(
        game: "Game",
        team1: Sequence["Player"],
        team2: Sequence["Player"],
        rating_types: Optional[List[str]] = None,
        *,
        mov_top: float = 1.25,
        timestamp_tz: _dt.tzinfo = _dt.timezone.utc,
) -> None:
    """
    Simple team Elo for foosball.

    - Team strength = average player rating
    - Win expectancy = standard Elo logistic
    - Team delta = K * margin_multiplier * (score - expected)
    - Delta is split equally among teammates
    - Sigma is retained in storage for compatibility, but not used or updated
    """
    if not team1 or not team2:
        raise ValueError("Both teams must be non-empty.")

    ids1, ids2 = {p.id for p in team1}, {p.id for p in team2}
    if ids1 & ids2:
        raise ValueError("A player cannot be on both teams.")

    now = _dt.datetime.now(timestamp_tz)
    first_of_year, first_of_month = _period_starts(now)
    game_ts = _normalize_ts(getattr(game, "game_timestamp", None), timestamp_tz)

    if rating_types is None:
        rating_types = _rating_types_for_game(game_ts, first_of_year, first_of_month)

    if game.result_team1 > game.result_team2:
        s1, s2 = 1.0, 0.0
    elif game.result_team1 < game.result_team2:
        s1, s2 = 0.0, 1.0
    else:
        s1 = s2 = 0.5

    K = float(getattr(game, "K", None) or 16.0)
    mov = _mov_multiplier(game.result_team1, game.result_team2, mov_top=mov_top)
    ts = game_ts or now

    def _getter(obj: Any, base: str) -> Callable[[str], float]:
        method = getattr(obj, f"get_{base}", None)
        if callable(method):
            return lambda rt: float(method(rt))

        def _get(rt: str) -> float:
            return float(getattr(obj, f"{base}_{rt}"))

        return _get

    def _setter(obj: Any, base: str) -> Callable[[str, float], None]:
        method = getattr(obj, f"set_{base}", None)
        if callable(method):
            return lambda rt, val: method(rt, float(val))

        def _set(rt: str, val: float) -> None:
            setattr(obj, f"{base}_{rt}", float(val))

        return _set

    for rating_type in rating_types:
        def player_mu(player: "Player") -> float:
            if player.rating is None:
                raise ValueError(f"Player {player.id} is missing a rating row")
            return _getter(player.rating, "mu")(rating_type)

        team1_rating = sum(player_mu(p) for p in team1) / len(team1)
        team2_rating = sum(player_mu(p) for p in team2) / len(team2)

        def expected(cur_rating: float, opp_rating: float) -> float:
            return 1.0 / (1.0 + 10.0 ** ((opp_rating - cur_rating) / 400.0))

        e1 = expected(team1_rating, team2_rating)
        e2 = 1.0 - e1

        delta_team1 = K * mov * (s1 - e1)
        delta_team2 = K * mov * (s2 - e2)

        split1 = delta_team1 / len(team1)
        split2 = delta_team2 / len(team2)

        for player in team1:
            if player.rating is None:
                raise ValueError(f"Player {player.id} is missing a rating row")
            get_mu = _getter(player.rating, "mu")
            set_mu = _setter(player.rating, "mu")
            set_mu(rating_type, get_mu(rating_type) + split1)
            setattr(player.rating, "last_updated", ts)

        for player in team2:
            if player.rating is None:
                raise ValueError(f"Player {player.id} is missing a rating row")
            get_mu = _getter(player.rating, "mu")
            set_mu = _setter(player.rating, "mu")
            set_mu(rating_type, get_mu(rating_type) + split2)
            setattr(player.rating, "last_updated", ts)


def recalculate_all_ratings(session: "Session") -> None:
    """
    Rebuild current ratings by replaying every saved game in chronological order.

    Monthly/yearly ratings are rebuilt using the same current-window logic as
    normal live updates.
    """
    now = _dt.datetime.now(tz=settings.tz)
    first_of_year, first_of_month = _period_starts(now)

    players = session.exec(
        select(Player).options(selectinload(Player.rating))
    ).all()

    for player in players:
        if player.rating is None:
            player.rating = CurrentPlayerRank(
                player_id=player.id,
                mu_overall=DEFAULT_RATING,
                sigma_overall=DEFAULT_SIGMA,
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                mu_yearly=DEFAULT_RATING,
                sigma_yearly=DEFAULT_SIGMA,
                last_updated=now,
            )
            session.add(player.rating)
        else:
            player.rating.mu_overall = DEFAULT_RATING
            player.rating.sigma_overall = DEFAULT_SIGMA
            player.rating.mu_monthly = DEFAULT_RATING
            player.rating.sigma_monthly = DEFAULT_SIGMA
            player.rating.mu_yearly = DEFAULT_RATING
            player.rating.sigma_yearly = DEFAULT_SIGMA
            player.rating.last_updated = now

    session.flush()
    session.exec(delete(GamePlayerRatingChange))

    games = session.exec(
        select(Game)
        .options(
            selectinload(Game.teams)
            .selectinload(Team.player)
            .selectinload(Player.rating)
        )
        .order_by(Game.game_timestamp.asc(), Game.id.asc())
    ).all()

    for game in games:
        team1: list[Player] = []
        team2: list[Player] = []

        for team in game.teams:
            player = team.player
            if player is None:
                raise ValueError(f"Game {game.id} references missing player_id={team.player_id}")

            if team.team_number == 1:
                team1.append(player)
            elif team.team_number == 2:
                team2.append(player)
            else:
                raise ValueError(f"Game {game.id} has invalid team_number={team.team_number}")

        if not team1 or not team2:
            raise ValueError(f"Game {game.id} must have players on both teams")

        game_ts = _normalize_ts(game.game_timestamp, settings.tz)
        rating_types = _rating_types_for_game(game_ts, first_of_year, first_of_month)

        players_in_game = team1 + team2
        before = snapshot_player_ratings(players_in_game, rating_types)

        update_all_ratings(
            game,
            team1,
            team2,
            rating_types=rating_types,
            timestamp_tz=settings.tz,
        )

        after = snapshot_player_ratings(players_in_game, rating_types)

        for row in build_game_rating_change_rows(
                game.id,
                players_in_game,
                before,
                after,
                rating_types,
        ):
            session.add(row)