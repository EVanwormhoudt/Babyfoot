import datetime as _dt
from typing import Any, Callable, Dict, List, Optional, Sequence, TYPE_CHECKING

from sqlalchemy.orm import selectinload
from sqlalchemy import delete
from sqlmodel import select

from ..consts import DEFAULT_RATING, DEFAULT_SIGMA
from ..db.models import CurrentPlayerRank, Game, Player, Team, GamePlayerRatingChange
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


def update_all_ratings(
        game: "Game",
        team1: Sequence["Player"],
        team2: Sequence["Player"],
        rating_types: Optional[List[str]] = None,
        *,
        # Margin handling for 0..10 scoring
        mu_margin_top: float = 1.5,   # μ multiplier goes from 1.0..mu_margin_top (gentle & stable)
        sigma_margin_top: float = 1.2,# σ multiplier goes from 1.0..sigma_margin_top
        # Core knobs
        c_effect: float = 2.0,        # how much σ reduces effective strength
        K_sigma: float = 6.0,         # sigma update strength (small)
        sigma_min: float = 45.0,
        sigma_max: float = float(DEFAULT_SIGMA),
        timestamp_tz: _dt.tzinfo = _dt.timezone.utc,
        # Optional per-player weights (e.g., minutes played): {player_id: weight}
        weights: Optional[Dict[int, float]] = None,
) -> None:
    """
    Team-level Elo with Margin-of-Victory (MoV).

    Steps per rating_type:
      1) Compute team effective ratings: mean(mu - c*sigma)
      2) Expected team score via logistic: E = 1 / (1 + 10^((opp - cur)/400))
      3) Team delta: Δteam = K * M_margin * (S - E), where M_margin ∈ [1, mu_margin_top]
      4) Split Δteam across teammates (weighted). Higher-Elo winners gain less;
         higher-Elo losers lose more.
      5) σ updates are gentle, also scaled by a smaller margin multiplier.

    Notes:
      - Uses game.K if present; else defaults to 16.
      - Works whether rating exposes get_mu()/set_mu() or mu_<type> attributes.
    """
    if rating_types is None:
        rating_types = ["overall", "monthly", "yearly"]

    if not team1 or not team2:
        raise ValueError("Both teams must be non-empty.")
    ids1, ids2 = {p.id for p in team1}, {p.id for p in team2}
    if ids1 & ids2:
        raise ValueError("A player cannot be on both teams.")

    # Outcome S (team-level)
    if game.result_team1 > game.result_team2:
        s1, s2 = 1.0, 0.0
    elif game.result_team1 < game.result_team2:
        s1, s2 = 0.0, 1.0
    else:
        s1 = s2 = 0.5

    # Margin multipliers (linear over 0..10, clamped to 10)
    margin = min(10, abs(int(game.result_team1) - int(game.result_team2)))
    margin_ratio = margin / 10.0
    M_mu = 1.0 + (mu_margin_top - 1.0) * margin_ratio
    M_sigma = 1.0 + (sigma_margin_top - 1.0) * margin_ratio

    # Base K for μ
    K = getattr(game, "K", 16)

    # Timestamp: prefer game timestamp if provided
    def _safe_ts() -> _dt.datetime:
        gts = getattr(game, "game_timestamp", None)
        if isinstance(gts, _dt.datetime):
            if gts.tzinfo is None:
                return gts.replace(tzinfo=timestamp_tz)
            return gts.astimezone(timestamp_tz)
        return _dt.datetime.now(timestamp_tz)

    ts = _safe_ts()

    # Accessor helpers (work with methods or attributes)
    def _getter(obj: Any, base: str) -> Callable[[str], float]:
        m = getattr(obj, f"get_{base}", None)
        if callable(m):
            return lambda rt: float(m(rt))
        def _get(rt: str) -> float:
            return float(getattr(obj, f"{base}_{rt}"))
        return _get

    def _setter(obj: Any, base: str) -> Callable[[str, float], None]:
        m = getattr(obj, f"set_{base}", None)
        if callable(m):
            return lambda rt, val: m(rt, float(val))
        def _set(rt: str, val: float) -> None:
            setattr(obj, f"{base}_{rt}", float(val))
        return _set

    # Optional external weighting (e.g., minutes played)
    def _weights_for(team: Sequence["Player"]) -> Dict[int, float]:
        if not weights:
            return {p.id: 1.0 for p in team}
        w = {p.id: max(0.0, float(weights.get(p.id, 1.0))) for p in team}
        if sum(w.values()) == 0.0:
            return {p.id: 1.0 for p in team}
        return w

    w1 = _weights_for(team1)
    w2 = _weights_for(team2)

    # Core per-rating loop
    for rating_type in rating_types:
        def shares_for(team: Sequence["Player"], base_w: Dict[int, float], team_delta: float) -> Dict[int, float]:
            if len(team) == 1:
                return {team[0].id: 1.0}

            # Draws keep a neutral split.
            if abs(team_delta) < 1e-12:
                neutral_total = sum(base_w[p.id] for p in team)
                if neutral_total <= 0.0:
                    return {p.id: 1.0 / len(team) for p in team}
                return {p.id: base_w[p.id] / neutral_total for p in team}

            # Winners (positive delta): lower Elo gets larger share.
            # Losers  (negative delta): higher Elo gets larger share.
            raw: Dict[int, float] = {}
            for p in team:
                r = p.rating
                get_mu = _getter(r, "mu")
                mu = max(100.0, get_mu(rating_type))
                elo_factor = (1.0 / mu) if team_delta > 0 else mu
                raw[p.id] = base_w[p.id] * elo_factor

            total = sum(raw.values())
            if total <= 0.0:
                return {p.id: 1.0 / len(team) for p in team}
            return {p.id: raw[p.id] / total for p in team}

        # Team effective ratings
        def eff(p: "Player") -> float:
            r = p.rating
            mu = _getter(r, "mu")(rating_type)
            sg = _getter(r, "sigma")(rating_type)
            return mu - c_effect * sg

        team1_eff = sum(eff(p) for p in team1) / len(team1)
        team2_eff = sum(eff(p) for p in team2) / len(team2)

        # Expected team scores (logistic on 400-scale)
        def expected(opp_eff: float, cur_eff: float) -> float:
            return 1.0 / (1.0 + 10.0 ** ((opp_eff - cur_eff) / 400.0))

        E1 = expected(team2_eff, team1_eff)
        E2 = 1.0 - E1  # symmetric

        # Team deltas with margin multiplier
        delta_team1 = K * M_mu * (s1 - E1)
        delta_team2 = K * M_mu * (s2 - E2)  # should be -delta_team1 (up to rounding)
        shares_t1 = shares_for(team1, w1, delta_team1)
        shares_t2 = shares_for(team2, w2, delta_team2)

        # Apply μ updates: split team delta among teammates
        for p in team1:
            r = p.rating
            get_mu = _getter(r, "mu"); set_mu = _setter(r, "mu")
            share = shares_t1.get(p.id, 1.0 / len(team1))
            new_mu = get_mu(rating_type) + delta_team1 * share
            set_mu(rating_type, new_mu)

        for p in team2:
            r = p.rating
            get_mu = _getter(r, "mu"); set_mu = _setter(r, "mu")
            share = shares_t2.get(p.id, 1.0 / len(team2))
            new_mu = get_mu(rating_type) + delta_team2 * share
            set_mu(rating_type, new_mu)

        # σ updates: gentle, margin-aware, based on surprise |S - E|
        # Same perf error for all teammates on a side in team-level Elo
        perf_err_t1 = abs(s1 - E1)
        perf_err_t2 = abs(s2 - E2)

        for p in team1:
            r = p.rating
            get_s = _getter(r, "sigma"); set_s = _setter(r, "sigma")
            cur = get_s(rating_type)
            new = max(sigma_min, min(sigma_max, cur + K_sigma * M_sigma * (perf_err_t1 - 0.5)))
            set_s(rating_type, new)
            setattr(r, "last_updated", ts)

        for p in team2:
            r = p.rating
            get_s = _getter(r, "sigma"); set_s = _setter(r, "sigma")
            cur = get_s(rating_type)
            new = max(sigma_min, min(sigma_max, cur + K_sigma * M_sigma * (perf_err_t2 - 0.5)))
            set_s(rating_type, new)
            setattr(r, "last_updated", ts)


def recalculate_all_ratings(session: "Session") -> None:
    """
    Rebuild current ratings by replaying every saved game in chronological order.
    """
    now = _dt.datetime.now(tz=settings.tz)
    first_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

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

        game_ts = game.game_timestamp
        if game_ts is not None:
            if game_ts.tzinfo is None:
                game_ts = game_ts.replace(tzinfo=settings.tz)
            else:
                game_ts = game_ts.astimezone(settings.tz)

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
