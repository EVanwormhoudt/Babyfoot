from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Dict, Tuple, List

from sqlalchemy.orm import selectinload
from sqlmodel import select

from backend.db.session import get_session
from backend.db.models import (
    Game,
    Player,
    Team,
    CurrentPlayerRank,
    PlayerRatingHistory,
)
from backend.ranking.custom_elo import update_all_ratings

RATING_TYPES = ("overall", "monthly", "yearly")
INIT_MU = 1000.0
INIT_SIGMA = 400.0


def ensure_current_rank(player: Player) -> CurrentPlayerRank:
    now = datetime.datetime.utcnow()
    if player.rating is None:
        player.rating = CurrentPlayerRank(
            player_id=player.id,
            mu_overall=INIT_MU, sigma_overall=INIT_SIGMA,
            mu_monthly=INIT_MU, sigma_monthly=INIT_SIGMA,
            mu_yearly=INIT_MU, sigma_yearly=INIT_SIGMA,
            last_updated=now,
        )
    else:
        if player.rating.mu_overall is None: player.rating.mu_overall = INIT_MU
        if player.rating.sigma_overall is None: player.rating.sigma_overall = INIT_SIGMA
        if player.rating.mu_monthly is None: player.rating.mu_monthly = INIT_MU
        if player.rating.sigma_monthly is None: player.rating.sigma_monthly = INIT_SIGMA
        if player.rating.mu_yearly is None: player.rating.mu_yearly = INIT_MU
        if player.rating.sigma_yearly is None: player.rating.sigma_yearly = INIT_SIGMA
        if player.rating.last_updated is None: player.rating.last_updated = now
    return player.rating


def compute_ranks(players: List[Player], rating_type: str) -> Dict[int, int]:
    """Ranks by mu (1 = best), ties share rank (1,2,2,4…)."""
    scored = []
    for p in players:
        cr = p.rating
        mu = cr.get_mu(rating_type) if cr else INIT_MU
        scored.append((p.id, mu))
    scored.sort(key=lambda x: x[1], reverse=True)
    ranks = {}
    prev_mu = None
    current_rank = 0
    for idx, (pid, mu) in enumerate(scored, start=1):
        if prev_mu is None or mu < prev_mu:
            current_rank = idx
        ranks[pid] = current_rank
        prev_mu = mu
    return ranks


def history_exists(session, player_id: int, rating_type: str, date_: datetime.date) -> bool:
    existing = session.exec(
        select(PlayerRatingHistory)
        .where(PlayerRatingHistory.player_id == player_id)
        .where(PlayerRatingHistory.rank_type == rating_type)
        .where(PlayerRatingHistory.date == date_)
        .limit(1)
    ).first()
    return existing is not None


def snapshot_month_end(session, players: List[Player], snapshot_date: datetime.date):
    """
    Save exactly one row per player & rating_type for the month that just ended,
    using the current mu/sigma values (after all games in that month).
    """
    ranks_per_type = {rt: compute_ranks(players, rt) for rt in RATING_TYPES}
    for p in players:
        cr = ensure_current_rank(p)
        for rt in RATING_TYPES:
            if not history_exists(session, p.id, rt, snapshot_date):
                prh = PlayerRatingHistory(
                    player_id=p.id,
                    mu=cr.get_mu(rt),
                    sigma=cr.get_sigma(rt),
                    date=snapshot_date,
                    rank=ranks_per_type[rt][p.id],
                    rank_type=rt,
                )
                session.add(prh)


def reset_monthly(players: List[Player]):
    """Reset monthly mu/sigma to baseline (1000/400) for all players."""
    for p in players:
        cr = ensure_current_rank(p)
        cr.mu_monthly = INIT_MU
        cr.sigma_monthly = INIT_SIGMA


def reset_yearly(players: List[Player]):
    """Reset yearly mu/sigma to baseline (1000/400) for all players."""
    for p in players:
        cr = ensure_current_rank(p)
        cr.mu_yearly = INIT_MU
        cr.sigma_yearly = INIT_SIGMA


def main():
    session = next(get_session())

    # Load players & ensure baseline ratings
    players: List[Player] = session.exec(
        select(Player).options(
            selectinload(Player.rating),
            selectinload(Player.rating_history),
        )
    ).all()
    for p in players:
        ensure_current_rank(p)
    session.commit()

    players_by_id = {p.id: p for p in players}

    # Load games and sort chronologically
    games: List[Game] = session.exec(
        select(Game).options(selectinload(Game.teams))
    ).all()
    games.sort(key=lambda g: (g.game_timestamp or datetime.datetime.min, g.id))

    active_month_key: Tuple[int, int] | None = None  # (year, month)
    active_year: int | None = None
    last_date_in_active_month: datetime.date | None = None

    for game in games:
        game_dt = game.game_timestamp or datetime.datetime.utcnow()
        game_date = game_dt.date()
        month_key = (game_date.year, game_date.month)
        year = game_date.year

        # If month changed, snapshot previous month once, then reset monthly
        if active_month_key is not None and month_key != active_month_key:
            # snapshot last month at the date of its last game
            snapshot_month_end(session, players, last_date_in_active_month)
            session.commit()
            # reset monthly baselines for the new month
            reset_monthly(players)
            session.commit()

        # If year changed, reset yearly (after Dec snapshot already captured above)
        if active_year is not None and year != active_year:
            reset_yearly(players)
            session.commit()

        # Update trackers
        active_month_key = month_key
        active_year = year
        last_date_in_active_month = game_date

        # Build team rosters
        team_map: Dict[int, List[Player]] = defaultdict(list)
        for tm in game.teams:
            p = players_by_id.get(tm.player_id)
            if p is not None:
                team_map[tm.team_number].append(p)

        team1 = team_map.get(1, [])
        team2 = team_map.get(2, [])
        if not team1 or not team2:
            continue  # skip malformed games

        # Mutating update
        update_all_ratings(game, team1, team2)

        # Update last_updated for participants
        for p in list(team1 + team2):
            ensure_current_rank(p).last_updated = game_dt

    # After loop: snapshot the final month once
    if active_month_key and last_date_in_active_month:
        snapshot_month_end(session, players, last_date_in_active_month)
        session.commit()

    # Optional: quick summary
    for p in players:
        cr = ensure_current_rank(p)
        print(
            f"{p.player_name} | "
            f"Overall {cr.mu_overall:.1f}±{cr.sigma_overall:.1f} | "
            f"Monthly {cr.mu_monthly:.1f}±{cr.sigma_monthly:.1f} | "
            f"Yearly {cr.mu_yearly:.1f}±{cr.sigma_yearly:.1f}"
        )


if __name__ == "__main__":
    main()
