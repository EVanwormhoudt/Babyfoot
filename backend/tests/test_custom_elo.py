import datetime as dt
import unittest
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from backend.consts import DEFAULT_SIGMA

try:
    from backend.ranking.custom_elo import _mov_multiplier, update_all_ratings
except ModuleNotFoundError:
    _mov_multiplier = None
    update_all_ratings = None


@dataclass
class DummyRank:
    mu_overall: float = 1000.0
    sigma_overall: float = float(DEFAULT_SIGMA)
    mu_monthly: float = 1000.0
    sigma_monthly: float = float(DEFAULT_SIGMA)
    mu_yearly: float = 1000.0
    sigma_yearly: float = float(DEFAULT_SIGMA)
    last_updated: dt.datetime | None = None

    def get_mu(self, rating_type: str) -> float:
        return float(getattr(self, f"mu_{rating_type}"))

    def set_mu(self, rating_type: str, value: float) -> None:
        setattr(self, f"mu_{rating_type}", float(value))

    def get_sigma(self, rating_type: str) -> float:
        return float(getattr(self, f"sigma_{rating_type}"))

    def set_sigma(self, rating_type: str, value: float) -> None:
        setattr(self, f"sigma_{rating_type}", float(value))


@dataclass
class DummyPlayer:
    id: int
    rating: DummyRank


@dataclass
class DummyGame:
    result_team1: int
    result_team2: int
    game_timestamp: dt.datetime | None = None
    K: int = 16


@unittest.skipIf(update_all_ratings is None or _mov_multiplier is None, "Project dependencies are missing")
class UpdateAllRatingsRegressionTests(unittest.TestCase):
    def _run_head_to_head(self, score_team1: int, score_team2: int, *, game_timestamp: dt.datetime | None = None):
        p1 = DummyPlayer(id=1, rating=DummyRank())
        p2 = DummyPlayer(id=2, rating=DummyRank())
        game = DummyGame(
            result_team1=score_team1,
            result_team2=score_team2,
            game_timestamp=game_timestamp,
        )
        update_all_ratings(
            game,
            [p1],
            [p2],
            rating_types=["overall"],
            timestamp_tz=dt.timezone.utc,
        )
        return p1, p2

    def test_margin_multiplier_is_clamped_to_ten(self):
        winner_10, loser_10 = self._run_head_to_head(10, 0)
        winner_50, loser_50 = self._run_head_to_head(50, 0)

        delta_winner_10 = winner_10.rating.mu_overall - 1000.0
        delta_winner_50 = winner_50.rating.mu_overall - 1000.0
        delta_loser_10 = loser_10.rating.mu_overall - 1000.0
        delta_loser_50 = loser_50.rating.mu_overall - 1000.0

        self.assertAlmostEqual(delta_winner_10, delta_winner_50, places=9)
        self.assertAlmostEqual(delta_loser_10, delta_loser_50, places=9)

    def test_sigma_starts_stable_at_default_sigma(self):
        winner, loser = self._run_head_to_head(10, 0)
        self.assertEqual(winner.rating.sigma_overall, float(DEFAULT_SIGMA))
        self.assertEqual(loser.rating.sigma_overall, float(DEFAULT_SIGMA))

    def test_last_updated_uses_game_timestamp_and_converts_timezone(self):
        paris_ts = dt.datetime(2026, 2, 14, 21, 5, tzinfo=ZoneInfo("Europe/Paris"))
        winner, loser = self._run_head_to_head(10, 0, game_timestamp=paris_ts)
        expected = paris_ts.astimezone(dt.timezone.utc)

        self.assertEqual(winner.rating.last_updated, expected)
        self.assertEqual(loser.rating.last_updated, expected)

    def test_mov_multiplier_matches_requested_bounds(self):
        self.assertAlmostEqual(_mov_multiplier(10, 9), 1.0, places=9)
        self.assertAlmostEqual(_mov_multiplier(10, 0), 2.0, places=9)
        self.assertAlmostEqual(_mov_multiplier(10, -90), 2.0, places=9)

    def test_mov_multiplier_accelerates_near_top(self):
        step_low = _mov_multiplier(10, 8) - _mov_multiplier(10, 9)  # margin 2 - margin 1
        step_high = _mov_multiplier(10, 0) - _mov_multiplier(10, 1)  # margin 10 - margin 9
        self.assertGreater(step_high, step_low)

    def test_default_rating_types_include_yearly_and_monthly_for_dated_games(self):
        p1 = DummyPlayer(id=1, rating=DummyRank())
        p2 = DummyPlayer(id=2, rating=DummyRank())
        game = DummyGame(
            result_team1=10,
            result_team2=7,
            # Keep this in the past relative to "now" so we guard against
            # regressions that only included the current year.
            game_timestamp=dt.datetime(2025, 6, 1, 12, 0, tzinfo=dt.timezone.utc),
        )

        update_all_ratings(
            game,
            [p1],
            [p2],
            rating_types=None,
            timestamp_tz=dt.timezone.utc,
        )

        self.assertNotEqual(p1.rating.mu_overall, 1000.0)
        self.assertNotEqual(p1.rating.mu_yearly, 1000.0)
        self.assertNotEqual(p1.rating.mu_monthly, 1000.0)

    def test_default_rating_types_for_undated_games_stay_overall_only(self):
        p1 = DummyPlayer(id=1, rating=DummyRank())
        p2 = DummyPlayer(id=2, rating=DummyRank())
        game = DummyGame(
            result_team1=10,
            result_team2=7,
            game_timestamp=None,
        )

        update_all_ratings(
            game,
            [p1],
            [p2],
            rating_types=None,
            timestamp_tz=dt.timezone.utc,
        )

        self.assertNotEqual(p1.rating.mu_overall, 1000.0)
        self.assertEqual(p1.rating.mu_yearly, 1000.0)
        self.assertEqual(p1.rating.mu_monthly, 1000.0)


if __name__ == "__main__":
    unittest.main()
