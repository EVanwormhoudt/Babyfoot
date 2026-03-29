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
    snapshot_player_ratings,
    update_all_ratings,
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
    current_day: dt.date | None = None
    previous_overall_snapshot: Dict[int, tuple[float, float]] = {}

    def snapshot_daily_overall_if_changed(snapshot_date: dt.date) -> None:
        ranks = _compute_dense_ranks(players, "overall")
        for p in players:
            mu = float(p.rating.get_mu("overall"))
            sigma = float(p.rating.get_sigma("overall"))
            prev = previous_overall_snapshot.get(p.id)
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
                    rank_type="overall",
                )
            )
            previous_overall_snapshot[p.id] = (mu, sigma)
            stats.history_rows += 1
            stats.history_overall_rows += 1

    def snapshot_monthly_and_yearly(snapshot_date: dt.date) -> None:
        for rating_type in ("monthly", "yearly"):
            ranks = _compute_dense_ranks(players, rating_type)
            for p in players:
                session.add(
                    PlayerRatingHistory(
                        player_id=p.id,
                        mu=float(p.rating.get_mu(rating_type)),
                        sigma=float(p.rating.get_sigma(rating_type)),
                        date=snapshot_date,
                        rank=ranks[p.id],
                        rank_type=rating_type,
                    )
                )
                stats.history_rows += 1
                if rating_type == "monthly":
                    stats.history_monthly_rows += 1
                else:
                    stats.history_yearly_rows += 1

    def reset_monthly() -> None:
        for p in players:
            p.rating.mu_monthly = DEFAULT_RATING
            p.rating.sigma_monthly = DEFAULT_SIGMA

    def reset_yearly() -> None:
        for p in players:
            p.rating.mu_yearly = DEFAULT_RATING
            p.rating.sigma_yearly = DEFAULT_SIGMA

    for game in games:
        game_ts = _normalize_game_timestamp(game)
        game_date = game_ts.date()
        month_key = (game_date.year, game_date.month)
        year = game_date.year

        if current_day is None:
            current_day = game_date
        elif game_date != current_day:
            snapshot_daily_overall_if_changed(current_day)
            current_day = game_date

        if active_month_key is not None and month_key != active_month_key:
            snapshot_monthly_and_yearly(last_date_in_active_month)
            reset_monthly()

        if active_year is not None and year != active_year:
            reset_yearly()

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
        before = snapshot_player_ratings(players_in_game, RATING_TYPES_ALL)
        update_all_ratings(
            game,
            team1,
            team2,
            rating_types=RATING_TYPES_ALL,
            timestamp_tz=settings.tz,
        )
        after = snapshot_player_ratings(players_in_game, RATING_TYPES_ALL)

        rows = build_game_rating_change_rows(
            game.id,
            players_in_game,
            before,
            after,
            RATING_TYPES_ALL,
        )
        for row in rows:
            session.add(row)
        stats.game_rating_changes += len(rows)

    if current_day is not None:
        snapshot_daily_overall_if_changed(current_day)

    if active_month_key is not None and last_date_in_active_month is not None:
        snapshot_monthly_and_yearly(last_date_in_active_month)

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
