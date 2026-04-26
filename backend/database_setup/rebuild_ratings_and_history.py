from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict

from sqlalchemy import delete, func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
from backend.db.models import (
    CurrentPlayerRank,
    Game,
    GamePlayerRatingChange,
    Player,
    PlayerRatingHistory,
    Team,
)
from backend.db.session import engine
from backend.ranking.custom_elo import (
    RATING_TYPES_ALL,
    build_game_rating_change_rows,
    calculate_game_rating_snapshots,
    snapshot_player_ratings,
)
from backend.settings import settings


@dataclass
class RebuildStats:
    games_total: int = 0
    games_skipped: int = 0
    game_rating_changes: int = 0
    history_rows: int = 0
    history_overall_rows: int = 0
    history_monthly_rows: int = 0
    history_yearly_rows: int = 0


def _next_month_start(month_key: tuple[int, int]) -> dt.date:
    year, month = month_key
    if month == 12:
        return dt.date(year + 1, 1, 1)
    return dt.date(year, month + 1, 1)


def _next_year_start(year: int) -> dt.date:
    return dt.date(year + 1, 1, 1)


def _normalize_game_timestamp(game: Game) -> dt.datetime:
    ts = game.game_timestamp
    if ts is None:
        # Keep undated matches deterministic and at the beginning of history.
        return dt.datetime(1970, 1, 1, tzinfo=settings.tz)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=settings.tz)
    return ts.astimezone(settings.tz)


def _compute_dense_ranks(players: list[Player], rating_type: str) -> Dict[int, int]:
    scored = []
    for p in players:
        mu = float(p.rating.get_mu(rating_type))
        sigma = float(p.rating.get_sigma(rating_type))
        scored.append((p.id, mu, sigma))
    scored.sort(key=lambda item: (-item[1], item[2], item[0]))

    ranks: Dict[int, int] = {}
    current_rank = 0
    previous_key = None
    for index, (player_id, mu, sigma) in enumerate(scored, start=1):
        key = (mu, sigma)
        if key != previous_key:
            current_rank = index
            previous_key = key
        ranks[player_id] = current_rank
    return ranks


def _ensure_and_reset_current_ranks(session: Session, players: list[Player]) -> None:
    now = dt.datetime.now(tz=settings.tz)
    for p in players:
        if p.rating is None:
            p.rating = CurrentPlayerRank(
                player_id=p.id,
                mu_overall=DEFAULT_RATING,
                sigma_overall=DEFAULT_SIGMA,
                mu_monthly=DEFAULT_RATING,
                sigma_monthly=DEFAULT_SIGMA,
                mu_yearly=DEFAULT_RATING,
                sigma_yearly=DEFAULT_SIGMA,
                last_updated=now,
            )
            session.add(p.rating)
        else:
            p.rating.mu_overall = DEFAULT_RATING
            p.rating.sigma_overall = DEFAULT_SIGMA
            p.rating.mu_monthly = DEFAULT_RATING
            p.rating.sigma_monthly = DEFAULT_SIGMA
            p.rating.mu_yearly = DEFAULT_RATING
            p.rating.sigma_yearly = DEFAULT_SIGMA
            p.rating.last_updated = now


def rebuild_all_ratings_and_history(session: Session) -> RebuildStats:
    stats = RebuildStats()

    players = session.exec(
        select(Player).options(selectinload(Player.rating))
    ).all()
    players.sort(key=lambda p: p.id)
    players_by_id = {p.id: p for p in players}

    _ensure_and_reset_current_ranks(session, players)
    session.flush()

    # Destructive reset (requested): remove previous per-game deltas and history points.
    session.exec(delete(GamePlayerRatingChange))
    session.exec(delete(PlayerRatingHistory))

    games = session.exec(
        select(Game)
        .options(
            selectinload(Game.teams)
            .selectinload(Team.player)
            .selectinload(Player.rating)
        )
        .order_by(Game.game_timestamp.asc(), Game.id.asc())
    ).all()
    stats.games_total = len(games)

    active_month_key: tuple[int, int] | None = None
    active_year: int | None = None
    last_date_in_active_month: dt.date | None = None
    current_day: object | dt.date | None = object()
    day_base_snapshot: Dict[tuple[int, str], Dict[str, float]] | None = None
    day_running_snapshot: Dict[tuple[int, str], Dict[str, float]] | None = None
    last_updated_by_player: Dict[int, dt.datetime] = {}
    previous_snapshots: Dict[str, Dict[int, tuple[float, float]]] = {
        "overall": {},
        "monthly": {},
        "yearly": {},
    }

    def snapshot_daily_if_changed(snapshot_date: dt.date, rating_type: str) -> None:
        ranks = _compute_dense_ranks(players, rating_type)
        previous_snapshot = previous_snapshots[rating_type]
        for p in players:
            mu = float(p.rating.get_mu(rating_type))
            sigma = float(p.rating.get_sigma(rating_type))
            prev = previous_snapshot.get(p.id)
            changed = prev is None or abs(mu - prev[0]) > 1e-9 or abs(sigma - prev[1]) > 1e-9
            if not changed:
                continue

            session.add(
                PlayerRatingHistory(
                    player_id=p.id,
                    mu=mu,
                    sigma=sigma,
                    date=snapshot_date,
                    rank=ranks[p.id],
                    rank_type=rating_type,
                )
            )
            previous_snapshot[p.id] = (mu, sigma)
            stats.history_rows += 1
            if rating_type == "overall":
                stats.history_overall_rows += 1
            elif rating_type == "monthly":
                stats.history_monthly_rows += 1
            else:
                stats.history_yearly_rows += 1

    def snapshot_all_daily_if_changed(snapshot_date: dt.date) -> None:
        for rating_type in ("overall", "monthly", "yearly"):
            snapshot_daily_if_changed(snapshot_date, rating_type)

    def reset_monthly() -> None:
        for p in players:
            p.rating.mu_monthly = DEFAULT_RATING
            p.rating.sigma_monthly = DEFAULT_SIGMA

    def reset_yearly() -> None:
        for p in players:
            p.rating.mu_yearly = DEFAULT_RATING
            p.rating.sigma_yearly = DEFAULT_SIGMA

    def finalize_day() -> None:
        nonlocal day_running_snapshot
        if day_running_snapshot is None:
            return
        for p in players:
            for rating_type in RATING_TYPES_ALL:
                values = day_running_snapshot[(p.id, rating_type)]
                p.rating.set_mu(rating_type, values["mu"])
                p.rating.set_sigma(rating_type, values["sigma"])
            if p.id in last_updated_by_player:
                p.rating.last_updated = last_updated_by_player[p.id]

    for game in games:
        game_ts = _normalize_game_timestamp(game)
        game_date = game_ts.date()
        month_key = (game_date.year, game_date.month)
        year = game_date.year

        if day_base_snapshot is None or game_date != current_day:
            if day_base_snapshot is not None and current_day is not None:
                finalize_day()
                snapshot_all_daily_if_changed(current_day)

            if active_month_key is not None and month_key != active_month_key:
                reset_monthly()
                monthly_reset_date = _next_month_start(active_month_key)
                if monthly_reset_date < game_date:
                    snapshot_daily_if_changed(monthly_reset_date, "monthly")

            if active_year is not None and year != active_year:
                reset_yearly()
                yearly_reset_date = _next_year_start(active_year)
                if yearly_reset_date < game_date:
                    snapshot_daily_if_changed(yearly_reset_date, "yearly")

            current_day = game_date
            day_base_snapshot = snapshot_player_ratings(players, RATING_TYPES_ALL)
            day_running_snapshot = {
                key: {"mu": float(values["mu"]), "sigma": float(values["sigma"])}
                for key, values in day_base_snapshot.items()
            }

        active_month_key = month_key
        active_year = year
        last_date_in_active_month = game_date

        team1: list[Player] = []
        team2: list[Player] = []
        for t in game.teams:
            p = players_by_id.get(t.player_id)
            if p is None:
                continue
            if t.team_number == 1:
                team1.append(p)
            elif t.team_number == 2:
                team2.append(p)

        if not team1 or not team2:
            stats.games_skipped += 1
            continue

        players_in_game = team1 + team2
        before, after, resolved_rating_types, ts = calculate_game_rating_snapshots(
            game,
            team1,
            team2,
            rating_types=RATING_TYPES_ALL,
            timestamp_tz=settings.tz,
            rating_snapshot=day_base_snapshot,
        )

        rows = build_game_rating_change_rows(
            game.id,
            players_in_game,
            before,
            after,
            resolved_rating_types,
        )
        for row in rows:
            session.add(row)
        stats.game_rating_changes += len(rows)

        if day_running_snapshot is None:
            raise ValueError("Daily replay snapshot was not initialized")

        for player in players_in_game:
            for rating_type in resolved_rating_types:
                key = (player.id, rating_type)
                day_running_snapshot[key]["mu"] += after[key]["mu"] - before[key]["mu"]
                day_running_snapshot[key]["sigma"] = after[key]["sigma"]
            last_updated_by_player[player.id] = ts

    if current_day is not None and day_base_snapshot is not None:
        finalize_day()
        snapshot_all_daily_if_changed(current_day)

    return stats


def _count_rows(session: Session) -> tuple[int, int, int]:
    games_count = session.exec(select(func.count()).select_from(Game)).one()
    history_count = session.exec(select(func.count()).select_from(PlayerRatingHistory)).one()
    changes_count = session.exec(select(func.count()).select_from(GamePlayerRatingChange)).one()
    return int(games_count), int(history_count), int(changes_count)


def main() -> None:
    with Session(engine) as session:
        before_games, before_history, before_changes = _count_rows(session)
        try:
            stats = rebuild_all_ratings_and_history(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        after_games, after_history, after_changes = _count_rows(session)

    print("✅ Full Elo rebuild complete")
    print(f"Games: {before_games} -> {after_games}")
    print(f"History rows: {before_history} -> {after_history}")
    print(f"Game rating change rows: {before_changes} -> {after_changes}")
    print(
        f"Rebuilt details: games_total={stats.games_total}, "
        f"games_skipped={stats.games_skipped}, "
        f"game_rating_changes={stats.game_rating_changes}, "
        f"history_rows={stats.history_rows} "
        f"(overall={stats.history_overall_rows}, "
        f"monthly={stats.history_monthly_rows}, "
        f"yearly={stats.history_yearly_rows})"
    )


if __name__ == "__main__":
    main()
