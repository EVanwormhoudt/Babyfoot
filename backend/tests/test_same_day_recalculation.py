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
    def _replay_same_day(self, ordered_scores: list[tuple[int, int]]):
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
            for index, (score_team1, score_team2) in enumerate(ordered_scores):
                game = Game(
                    game_timestamp=start + dt.timedelta(minutes=index * 5),
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


if __name__ == "__main__":
    unittest.main()
