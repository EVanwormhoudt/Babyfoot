import datetime as dt
import unittest

try:
    from starlette.requests import Request
    from sqlmodel import SQLModel, Session, create_engine

    from backend.api.players import list_players
    from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
    from backend.db.models import CurrentPlayerRank, Game, Player, Team
except ModuleNotFoundError:
    Request = None
    SQLModel = None
    Session = None
    create_engine = None
    list_players = None
    DEFAULT_RATING = None
    DEFAULT_SIGMA = None
    CurrentPlayerRank = None
    Game = None
    Player = None
    Team = None


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/players",
            "headers": [],
            "client": ("203.0.113.10", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


@unittest.skipIf(
    SQLModel is None or Session is None or list_players is None,
    "Project dependencies are missing",
)
class PlayerListTests(unittest.TestCase):
    def test_list_players_includes_latest_game_timestamp(self):
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

            now = dt.datetime(2026, 8, 30, 12, 0, tzinfo=dt.timezone.utc)
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
                        last_updated=now,
                    )
                )

            old_ts = dt.datetime(2026, 4, 15, 18, 0, tzinfo=dt.timezone.utc)
            recent_ts = dt.datetime(2026, 8, 10, 18, 0, tzinfo=dt.timezone.utc)
            old_game = Game(game_timestamp=old_ts, result_team1=10, result_team2=8)
            recent_game = Game(game_timestamp=recent_ts, result_team1=10, result_team2=4)
            session.add_all([old_game, recent_game])
            session.flush()
            session.add_all(
                [
                    Team(game_id=old_game.id, player_id=alice_id, team_number=1),
                    Team(game_id=old_game.id, player_id=bob_id, team_number=2),
                    Team(game_id=recent_game.id, player_id=alice_id, team_number=1),
                    Team(game_id=recent_game.id, player_id=bob_id, team_number=2),
                ]
            )
            session.commit()

            result = list_players(make_request(), limit=50, offset=0, session=session)

        by_id = {player.id: player for player in result}
        self.assertEqual(by_id[alice_id].last_game_timestamp.date(), recent_ts.date())
        self.assertEqual(by_id[bob_id].last_game_timestamp.date(), recent_ts.date())
        self.assertIsNone(by_id[charlie_id].last_game_timestamp)


if __name__ == "__main__":
    unittest.main()
