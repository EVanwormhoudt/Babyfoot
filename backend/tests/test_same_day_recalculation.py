import datetime as dt
import unittest

try:
    from sqlalchemy.orm import selectinload
    from sqlmodel import SQLModel, Session, create_engine, select

    from backend.consts import DEFAULT_RATING
    from backend.db.models import Game, Player, Team
    from backend.ranking.custom_elo import recalculate_all_ratings
except ModuleNotFoundError:
    SQLModel = None
    Session = None
    create_engine = None
    select = None
    selectinload = None
    DEFAULT_RATING = None
    Game = None
    Player = None
    Team = None
    recalculate_all_ratings = None


@unittest.skipIf(
    SQLModel is None or Session is None or recalculate_all_ratings is None,
    "Project dependencies are missing",
)
class SameDayRecalculationTests(unittest.TestCase):
    def _replay_same_day(self, ordered_scores: list[tuple[int, int]], *, prior_day_gap: int = 0):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            players = [
                Player(player_name="Alice", player_color="#f00", active=True),
                Player(player_name="Bob", player_color="#00f", active=True),
            ]
            for player in players:
                session.add(player)
            session.flush()

            start = dt.datetime(2026, 3, 18, 10, 0, tzinfo=dt.timezone.utc)
            game_specs = [
                (start + dt.timedelta(minutes=index * 5), score1, score2)
                for index, (score1, score2) in enumerate(ordered_scores)
            ]
            if prior_day_gap:
                game_specs.insert(0, (start - dt.timedelta(days=prior_day_gap), 0, 10))
            for timestamp, score_team1, score_team2 in game_specs:
                game = Game(
                    game_timestamp=timestamp,
                    result_team1=score_team1,
                    result_team2=score_team2,
                )
                session.add(game)
                session.flush()
                session.add(Team(game_id=game.id, player_id=players[0].id, team_number=1))
                session.add(Team(game_id=game.id, player_id=players[1].id, team_number=2))

            session.flush()
            recalculate_all_ratings(session)
            session.commit()

            games = session.exec(
                select(Game)
                .options(selectinload(Game.rating_changes))
                .order_by(Game.id.asc())
            ).all()
            players = session.exec(
                select(Player)
                .options(selectinload(Player.rating))
                .order_by(Player.id.asc())
            ).all()

        deltas: dict[tuple[int, int, int, str], tuple[float, float, float]] = {}
        for game in games:
            for row in game.rating_changes:
                deltas[(game.result_team1, game.result_team2, row.player_id, row.rating_type)] = (
                    round(float(row.delta_mu), 9),
                    round(float(row.mu_before), 9),
                    round(float(row.mu_after), 9),
                )

        current_ratings = {
            player.id: (
                round(float(player.rating.mu_overall), 9),
                round(float(player.rating.mu_monthly), 9),
                round(float(player.rating.mu_yearly), 9),
            )
            for player in players
            if player.rating is not None
        }
        return deltas, current_ratings

    def test_same_day_results_are_independent_from_creation_order(self):
        forward_deltas, forward_current = self._replay_same_day([(10, 0), (9, 10)])
        reverse_deltas, reverse_current = self._replay_same_day([(9, 10), (10, 0)])

        self.assertEqual(forward_deltas, reverse_deltas)
        self.assertEqual(forward_current, reverse_current)

        self.assertEqual(forward_current[1], (1008.0, float(DEFAULT_RATING), 1008.0))
        self.assertEqual(forward_current[2], (992.0, float(DEFAULT_RATING), 992.0))

        self.assertEqual(
            forward_deltas[(10, 0, 1, "overall")],
            (16.0, float(DEFAULT_RATING), 1016.0),
        )
        self.assertEqual(
            forward_deltas[(9, 10, 1, "overall")],
            (-8.0, float(DEFAULT_RATING), 992.0),
        )

    def test_day_baseline_is_previous_closing_rating_even_after_idle_days(self):
        for gap in (1, 4):
            with self.subTest(days_since_previous_match=gap):
                forward_deltas, forward_current = self._replay_same_day(
                    [(10, 0), (9, 10)], prior_day_gap=gap,
                )
                reverse_deltas, reverse_current = self._replay_same_day(
                    [(9, 10), (10, 0)], prior_day_gap=gap,
                )
                self.assertEqual(forward_deltas, reverse_deltas)
                self.assertEqual(forward_current, reverse_current)

                # Yesterday's 0-10 result closes at 984 / 1016. Both
                # matches today must use those strengths, even after a win.
                expected_alice = 1.0 / (1.0 + 10.0 ** (32.0 / 400.0))
                for rating_type in ("overall", "monthly", "yearly"):
                    win = forward_deltas[(10, 0, 1, rating_type)]
                    loss = forward_deltas[(9, 10, 1, rating_type)]
                    self.assertEqual(win[1], 984.0)
                    self.assertEqual(loss[1], 984.0)
                    self.assertAlmostEqual(win[0], 32.0 * (1.0 - expected_alice))
                    self.assertAlmostEqual(loss[0], -16.0 * expected_alice)
                    for score in ((10, 0), (9, 10)):
                        bob = forward_deltas[(*score, 2, rating_type)]
                        alice = forward_deltas[(*score, 1, rating_type)]
                        self.assertEqual(bob[1], 1016.0)
                        self.assertAlmostEqual(bob[0], -alice[0])
                self.assertAlmostEqual(
                    forward_current[1][0], 984.0 + win[0] + loss[0],
                )


if __name__ == "__main__":
    unittest.main()
