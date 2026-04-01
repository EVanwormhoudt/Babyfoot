import datetime as _dt
import math
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
DEFAULT_TEAMMATE_ADVANTAGE = 180.0


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


def _rating_types_for_game(
        game_ts: Optional[_dt.datetime],
) -> List[str]:
    rating_types = ["overall"]
    if game_ts is not None:
        rating_types.append("yearly")
        rating_types.append("monthly")
    return rating_types


def _team_size_bonus(
        team_size: int,
        *,
        team_size_advantage: float = DEFAULT_TEAMMATE_ADVANTAGE,
) -> float:
    """
    Extra expected-strength bonus for larger teams.

    A solo player (size=1) gets no bonus; size=2 gets one full bonus step.
    """
    if team_size <= 1 or team_size_advantage <= 0:
        return 0.0
    return float(team_size_advantage) * math.log2(float(team_size))


def _mov_multiplier(
        score1: float,
        score2: float,
        *,
        mov_top: float = 2.0,
        max_margin: float = 10.0,
        min_margin: float = 1.0,
        exp_k: float = 2.2,
) -> float:
    """
    Exponential margin-of-victory scaling for foosball.

    Targets:
      - margin=1  (e.g. 10-9) -> 1.0
      - margin=10 (e.g. 10-0) -> mov_top (default 2.0)
      - Larger step sizes near mov_top (convex curve)
    """
    margin = min(max_margin, abs(float(score1) - float(score2)))
    if max_margin <= min_margin:
        return float(mov_top)
    if margin <= min_margin:
        return 1.0

    x = (margin - min_margin) / (max_margin - min_margin)  # 0..1
    num = math.exp(exp_k * x) - 1.0
    den = math.exp(exp_k) - 1.0
    curve = num / den
    return 1.0 + (mov_top - 1.0) * curve


def update_all_ratings(
        game: "Game",
        team1: Sequence["Player"],
        team2: Sequence["Player"],
        rating_types: Optional[List[str]] = None,
        *,
        mov_top: float = 2.0,
        team_size_advantage: float = DEFAULT_TEAMMATE_ADVANTAGE,
        timestamp_tz: _dt.tzinfo = _dt.timezone.utc,
) -> None:
    """
    Simple team Elo for foosball.

    - Team strength = average player rating + teammate-count bonus
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
    game_ts = _normalize_ts(getattr(game, "game_timestamp", None), timestamp_tz)

    if rating_types is None:
        rating_types = _rating_types_for_game(game_ts)

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

        team1_rating = (
                (sum(player_mu(p) for p in team1) / len(team1))
                + _team_size_bonus(len(team1), team_size_advantage=team_size_advantage)
        )
        team2_rating = (
                (sum(player_mu(p) for p in team2) / len(team2))
                + _team_size_bonus(len(team2), team_size_advantage=team_size_advantage)
        )

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

    Monthly/yearly ratings are replayed across the full history with resets at
    month/year boundaries so per-game deltas are available for historical games.
    """
    now = _dt.datetime.now(tz=settings.tz)

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

    active_month_key: Optional[tuple[int, int]] = None
    active_year: Optional[int] = None

    def _reset_monthly() -> None:
        for player in players:
            if player.rating is None:
                continue
            player.rating.mu_monthly = DEFAULT_RATING
            player.rating.sigma_monthly = DEFAULT_SIGMA

    def _reset_yearly() -> None:
        for player in players:
            if player.rating is None:
                continue
            player.rating.mu_yearly = DEFAULT_RATING
            player.rating.sigma_yearly = DEFAULT_SIGMA

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
        if game_ts is not None:
            month_key = (game_ts.year, game_ts.month)
            if active_month_key is not None and month_key != active_month_key:
                _reset_monthly()

            if active_year is not None and game_ts.year != active_year:
                _reset_yearly()

            active_month_key = month_key
            active_year = game_ts.year

        rating_types = _rating_types_for_game(game_ts)

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

    # Keep current-period rank semantics consistent when there is no game in
    # the active month/year.
    if active_year is not None and active_year != now.year:
        _reset_yearly()

    current_month_key = (now.year, now.month)
    if active_month_key is not None and active_month_key != current_month_key:
        _reset_monthly()
