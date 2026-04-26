import datetime as dt
import unittest

try:
    from sqlalchemy.orm import selectinload
    from sqlmodel import SQLModel, Session, create_engine, select

    from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
    from backend.api.games import create_game
    from backend.db.models import CurrentPlayerRank, Game, Player
    from backend.schemas import GameCreate, TeamCreate
except ModuleNotFoundError:
    SQLModel = None
    Session = None
    create_engine = None
    select = None
    selectinload = None
    DEFAULT_RATING = None
    DEFAULT_SIGMA = None
    create_game = None
    CurrentPlayerRank = None
    Game = None
    Player = None
    GameCreate = None
    TeamCreate = None


@unittest.skipIf(
    SQLModel is None or Session is None or create_game is None,
    "Project dependencies are missing",
)
class SameDayCreateGameTests(unittest.TestCase):
    def _create_in_order(self, ordered_scores: list[tuple[int, int]]):
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

            for player in players:
                session.add(
                    CurrentPlayerRank(
                        player_id=player.id,
                        mu_overall=float(DEFAULT_RATING),
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=float(DEFAULT_RATING),
                        sigma_monthly=float(DEFAULT_SIGMA),
                        mu_yearly=float(DEFAULT_RATING),
                        sigma_yearly=float(DEFAULT_SIGMA),
                        last_updated=dt.datetime.now(dt.timezone.utc),
                    )
                )
            session.commit()

            for score_team1, score_team2 in ordered_scores:
                create_game(
                    GameCreate(
                        result_team1=score_team1,
                        result_team2=score_team2,
                        teams=[
                            TeamCreate(player_id=players[0].id, team_number=1),
                            TeamCreate(player_id=players[1].id, team_number=2),
                        ],
                    ),
                    session,
                )

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

    def test_same_day_creates_are_independent_from_creation_order(self):
        forward_deltas, forward_current = self._create_in_order([(10, 0), (9, 10)])
        reverse_deltas, reverse_current = self._create_in_order([(9, 10), (10, 0)])

        self.assertEqual(forward_deltas, reverse_deltas)
        self.assertEqual(forward_current, reverse_current)

        self.assertEqual(forward_current[1], (1008.0, 1008.0, 1008.0))
        self.assertEqual(forward_current[2], (992.0, 992.0, 992.0))

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
