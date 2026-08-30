import datetime as dt
import unittest

try:
    from sqlalchemy.dialects import postgresql
    from sqlmodel import SQLModel, Session, create_engine, select

    from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
    from backend.jobs import (
        _build_daily_snapshot_rows,
        _build_daily_overall_snapshot_rows,
        _has_snapshot_changed,
        _has_overall_snapshot_changed,
        _rank_type_expr,
        _snapshot_date_expr,
        _upsert_snapshot_rows,
        snapshot_missing_daily_ratings_if_safe,
    )
    from backend.db.models import CurrentPlayerRank, Game, Player, PlayerRatingHistory
except ModuleNotFoundError:
    DEFAULT_RATING = None
    DEFAULT_SIGMA = None
    _build_daily_snapshot_rows = None
    _build_daily_overall_snapshot_rows = None
    _has_snapshot_changed = None
    _has_overall_snapshot_changed = None
    _rank_type_expr = None
    _snapshot_date_expr = None
    _upsert_snapshot_rows = None
    snapshot_missing_daily_ratings_if_safe = None
    SQLModel = None
    Session = None
    create_engine = None
    select = None
    CurrentPlayerRank = None
    Game = None
    Player = None
    PlayerRatingHistory = None


@unittest.skipIf(
    _build_daily_overall_snapshot_rows is None or _has_overall_snapshot_changed is None,
    "Project dependencies are missing",
)
class DailyOverallSnapshotTests(unittest.TestCase):
    def test_change_detector(self):
        self.assertFalse(_has_snapshot_changed(1000.0, 400.0, 1000.0, 400.0))
        self.assertTrue(_has_snapshot_changed(1000.1, 400.0, 1000.0, 400.0))
        self.assertTrue(_has_snapshot_changed(1000.0, 399.9, 1000.0, 400.0))
        self.assertTrue(_has_snapshot_changed(1000.0, 400.0, None, None))

        self.assertFalse(_has_overall_snapshot_changed(1000.0, 400.0, 1000.0, 400.0))
        self.assertTrue(_has_overall_snapshot_changed(1000.1, 400.0, 1000.0, 400.0))
        self.assertTrue(_has_overall_snapshot_changed(1000.0, 399.9, 1000.0, 400.0))
        self.assertTrue(_has_overall_snapshot_changed(1000.0, 400.0, None, None))

    def test_build_daily_rows_only_for_changed_players(self):
        snapshot_date = dt.date(2026, 3, 28)
        candidates = [
            {"player_id": 1, "mu": 1012.0, "sigma": 400.0, "rank": 1},
            {"player_id": 2, "mu": 1000.0, "sigma": 400.0, "rank": 2},
            {"player_id": 3, "mu": 990.0, "sigma": 399.5, "rank": 3},
        ]
        latest = {
            1: (1000.0, 400.0),   # changed
            2: (1000.0, 400.0),   # unchanged
            3: (990.0, 400.0),    # sigma changed
        }

        rows = _build_daily_overall_snapshot_rows(
            candidates=candidates,
            latest_by_player=latest,
            snapshot_date=snapshot_date,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({int(row["player_id"]) for row in rows}, {1, 3})
        for row in rows:
            self.assertEqual(row["rank_type"], "overall")
            self.assertEqual(row["date"], snapshot_date)

    def test_build_daily_rows_only_for_changed_players_for_monthly(self):
        snapshot_date = dt.date(2026, 4, 2)
        candidates = [
            {"player_id": 1, "mu": 1012.0, "sigma": 400.0, "rank": 1},
            {"player_id": 2, "mu": 1000.0, "sigma": 400.0, "rank": 2},
        ]
        latest = {
            1: (1012.0, 400.0),
            2: (999.0, 400.0),
        }

        rows = _build_daily_snapshot_rows(
            candidates=candidates,
            latest_by_player=latest,
            snapshot_date=snapshot_date,
            rank_type="monthly",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0]["player_id"]), 2)
        self.assertEqual(rows[0]["rank_type"], "monthly")
        self.assertEqual(rows[0]["date"], snapshot_date)

    def test_snapshot_date_expr_compiles_to_bound_date_literal(self):
        compiled = str(_snapshot_date_expr(dt.date(2026, 3, 28)).compile(dialect=postgresql.dialect()))
        self.assertIn("CAST(", compiled)
        self.assertNotIn("literal(", compiled)

    def test_rank_type_expr_compiles_to_bound_literal(self):
        compiled = str(_rank_type_expr("monthly").compile(dialect=postgresql.dialect()))
        self.assertNotIn("literal(", compiled)

    def test_upsert_snapshot_rows_updates_existing_snapshot(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            player = Player(player_name="Alice", player_color="#f00", active=True)
            session.add(player)
            session.flush()

            snapshot_date = dt.date(2026, 4, 2)
            _upsert_snapshot_rows(
                session,
                [
                    {
                        "player_id": player.id,
                        "mu": 1012.0,
                        "sigma": 400.0,
                        "date": snapshot_date,
                        "rank": 2,
                        "rank_type": "monthly",
                    }
                ],
            )
            session.flush()
            _upsert_snapshot_rows(
                session,
                [
                    {
                        "player_id": player.id,
                        "mu": 1024.0,
                        "sigma": 399.0,
                        "date": snapshot_date,
                        "rank": 1,
                        "rank_type": "monthly",
                    }
                ],
            )
            session.commit()

            rows = session.exec(select(PlayerRatingHistory)).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].mu, 1024.0)
        self.assertEqual(rows[0].sigma, 399.0)
        self.assertEqual(rows[0].rank, 1)

    def test_snapshot_missing_daily_ratings_backfills_yesterday_when_safe(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            player = Player(player_name="Alice", player_color="#f00", active=True)
            session.add(player)
            session.flush()
            session.add(
                CurrentPlayerRank(
                    player_id=player.id,
                    mu_overall=1012.0,
                    sigma_overall=float(DEFAULT_SIGMA),
                    mu_monthly=1008.0,
                    sigma_monthly=float(DEFAULT_SIGMA),
                    mu_yearly=1010.0,
                    sigma_yearly=float(DEFAULT_SIGMA),
                    last_updated=dt.datetime(2026, 3, 31, 21, tzinfo=dt.timezone.utc),
                )
            )
            session.commit()

            row_count = snapshot_missing_daily_ratings_if_safe(
                session,
                now=dt.datetime(2026, 4, 1, 12, tzinfo=dt.timezone.utc),
            )
            session.commit()

            rows = session.exec(
                select(PlayerRatingHistory).order_by(PlayerRatingHistory.rank_type)
            ).all()

        self.assertEqual(row_count, 3)
        self.assertEqual({row.rank_type for row in rows}, {"overall", "monthly", "yearly"})
        self.assertEqual({row.date for row in rows}, {dt.date(2026, 3, 31)})

    def test_snapshot_missing_daily_ratings_skips_longer_gaps_that_need_rebuild(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            player = Player(player_name="Alice", player_color="#f00", active=True)
            session.add(player)
            session.flush()
            session.add(
                CurrentPlayerRank(
                    player_id=player.id,
                    mu_overall=1012.0,
                    sigma_overall=float(DEFAULT_SIGMA),
                    mu_monthly=1008.0,
                    sigma_monthly=float(DEFAULT_SIGMA),
                    mu_yearly=1010.0,
                    sigma_yearly=float(DEFAULT_SIGMA),
                    last_updated=dt.datetime(2026, 3, 30, 21, tzinfo=dt.timezone.utc),
                )
            )
            session.add(
                Game(
                    game_timestamp=dt.datetime(2026, 3, 30, 21, tzinfo=dt.timezone.utc),
                    result_team1=10,
                    result_team2=8,
                )
            )
            session.commit()

            with self.assertLogs("backend.jobs", level="WARNING") as logs:
                row_count = snapshot_missing_daily_ratings_if_safe(
                    session,
                    now=dt.datetime(2026, 4, 2, 12, tzinfo=dt.timezone.utc),
                )
            session.commit()

            rows = session.exec(select(PlayerRatingHistory)).all()

        self.assertEqual(row_count, 0)
        self.assertEqual(rows, [])
        self.assertIn("run backend.database_setup.rebuild_ratings_and_history", "\n".join(logs.output))

    def test_snapshot_missing_daily_ratings_skips_when_current_ratings_include_today(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            player = Player(player_name="Alice", player_color="#f00", active=True)
            session.add(player)
            session.flush()
            session.add(
                CurrentPlayerRank(
                    player_id=player.id,
                    mu_overall=1012.0,
                    sigma_overall=float(DEFAULT_SIGMA),
                    mu_monthly=1008.0,
                    sigma_monthly=float(DEFAULT_SIGMA),
                    mu_yearly=1010.0,
                    sigma_yearly=float(DEFAULT_SIGMA),
                    last_updated=dt.datetime(2026, 4, 1, 9, tzinfo=dt.timezone.utc),
                )
            )
            session.add(
                Game(
                    game_timestamp=dt.datetime(2026, 4, 1, 9, tzinfo=dt.timezone.utc),
                    result_team1=10,
                    result_team2=8,
                )
            )
            session.commit()

            with self.assertLogs("backend.jobs", level="WARNING") as logs:
                row_count = snapshot_missing_daily_ratings_if_safe(
                    session,
                    now=dt.datetime(2026, 4, 1, 12, tzinfo=dt.timezone.utc),
                )
            session.commit()

            rows = session.exec(select(PlayerRatingHistory)).all()

        self.assertEqual(row_count, 0)
        self.assertEqual(rows, [])
        self.assertIn("latest game is on 2026-04-01", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
