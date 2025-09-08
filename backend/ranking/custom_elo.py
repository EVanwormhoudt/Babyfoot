import datetime as _dt
import math
from typing import List, Sequence, Any, Callable, Optional, Dict


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
        sigma_max: float = 220.0,
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
      4) Split Δteam across teammates (equal or weighted). Winners up, losers down.
      5) σ updates are gentle, also scaled by a smaller margin multiplier.

    Notes:
      - Uses game.K if present; else defaults to 8.
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

    # Margin multipliers (bounded & linear over 0..10)
    margin = abs(int(game.result_team1) - int(game.result_team2))  # 0..10
    margin_ratio = margin / 10.0
    M_mu = 1.0 + (mu_margin_top - 1.0) * margin_ratio
    M_sigma = 1.0 + (sigma_margin_top - 1.0) * margin_ratio

    # Base K for μ
    K = getattr(game, "K", 16)

    # Timestamp: prefer game date/time if provided
    def _safe_ts() -> _dt.datetime:
        gd = getattr(game, "game_date", None)
        gt = getattr(game, "game_time", None)
        if gd and gt:
            if isinstance(gt, str):
                try:
                    hh, mm = map(int, gt.split(":")[:2])
                    t = _dt.time(hour=hh, minute=mm, tzinfo=timestamp_tz)
                except Exception:
                    t = _dt.time(tzinfo=timestamp_tz)
            elif isinstance(gt, _dt.time):
                t = gt.replace(tzinfo=timestamp_tz)
            else:
                t = _dt.time(tzinfo=timestamp_tz)
            if isinstance(gd, _dt.date) and not isinstance(gd, _dt.datetime):
                return _dt.datetime.combine(gd, t)
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

    # Weighting for splitting team delta (default equal)
    def _weights_for(team: Sequence["Player"]) -> Dict[int, float]:
        if not weights:
            return {p.id: 1.0 for p in team}
        w = {p.id: max(0.0, float(weights.get(p.id, 1.0))) for p in team}
        if sum(w.values()) == 0.0:
            return {p.id: 1.0 for p in team}
        return w

    w1 = _weights_for(team1)
    w2 = _weights_for(team2)
    sum_w1 = sum(w1.values())
    sum_w2 = sum(w2.values())

    # Core per-rating loop
    for rating_type in rating_types:
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

        # Apply μ updates: split team delta among teammates
        for p in team1:
            r = p.rating
            get_mu = _getter(r, "mu"); set_mu = _setter(r, "mu")
            share = (w1[p.id] / sum_w1) if sum_w1 > 0 else (1.0 / len(team1))
            new_mu = get_mu(rating_type) + delta_team1 * share
            set_mu(rating_type, new_mu)

        for p in team2:
            r = p.rating
            get_mu = _getter(r, "mu"); set_mu = _setter(r, "mu")
            share = (w2[p.id] / sum_w2) if sum_w2 > 0 else (1.0 / len(team2))
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
