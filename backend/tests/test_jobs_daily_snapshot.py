import datetime as dt
import unittest

try:
    from sqlalchemy.dialects import postgresql

    from backend.jobs import (
        _build_daily_snapshot_rows,
        _build_daily_overall_snapshot_rows,
        _has_snapshot_changed,
        _has_overall_snapshot_changed,
        _rank_type_expr,
        _snapshot_date_expr,
    )
except ModuleNotFoundError:
    _build_daily_snapshot_rows = None
    _build_daily_overall_snapshot_rows = None
    _has_snapshot_changed = None
    _has_overall_snapshot_changed = None
    _rank_type_expr = None
    _snapshot_date_expr = None


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


if __name__ == "__main__":
    unittest.main()
