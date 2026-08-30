import datetime as dt
import unittest

try:
    from starlette.requests import Request
    from sqlmodel import SQLModel, Session, create_engine

    from backend.api.games import get_games
    from backend.db.models import Game, Player, Team
except ModuleNotFoundError:
    Request = None
    SQLModel = None
    Session = None
    create_engine = None
    get_games = None
    Game = None
    Player = None
    Team = None


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/games",
            "headers": [],
            "client": ("203.0.113.10", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


@unittest.skipIf(
    SQLModel is None or Session is None or get_games is None,
    "Project dependencies are missing",
)
class GamePlayerFilterTests(unittest.TestCase):
    def test_get_games_filters_by_player_and_total(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            players = [
                Player(player_name="Alice", player_color="#f00", active=True),
                Player(player_name="Bob", player_color="#00f", active=True),
                Player(player_name="Charlie", player_color="#0f0", active=True),
            ]
            session.add_all(players)
            session.flush()
            alice_id, bob_id, charlie_id = [player.id for player in players]

            game_1 = Game(
                game_timestamp=dt.datetime(2026, 8, 1, 12, 0, tzinfo=dt.timezone.utc),
                result_team1=10,
                result_team2=8,
            )
            game_2 = Game(
                game_timestamp=dt.datetime(2026, 8, 2, 12, 0, tzinfo=dt.timezone.utc),
                result_team1=6,
                result_team2=10,
            )
            game_3 = Game(
                game_timestamp=dt.datetime(2026, 8, 3, 12, 0, tzinfo=dt.timezone.utc),
                result_team1=10,
                result_team2=2,
            )
            session.add_all([game_1, game_2, game_3])
            session.flush()
            session.add_all(
                [
                    Team(game_id=game_1.id, player_id=alice_id, team_number=1),
                    Team(game_id=game_1.id, player_id=bob_id, team_number=2),
                    Team(game_id=game_2.id, player_id=bob_id, team_number=1),
                    Team(game_id=game_2.id, player_id=charlie_id, team_number=2),
                    Team(game_id=game_3.id, player_id=alice_id, team_number=1),
                    Team(game_id=game_3.id, player_id=charlie_id, team_number=2),
                ]
            )
            session.commit()

            result = get_games(
                make_request(),
                session=session,
                scope="all",
                limit=10,
                offset=0,
                start_date=None,
                end_date=None,
                player_id=alice_id,
            )

        self.assertEqual(result["total"], 2)
        self.assertEqual([game.id for game in result["items"]], [game_3.id, game_1.id])
        for game in result["items"]:
            self.assertIn(alice_id, {team.player_id for team in game.teams})


if __name__ == "__main__":
    unittest.main()
