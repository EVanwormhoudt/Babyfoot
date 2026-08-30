import datetime as dt
import unittest

try:
    from starlette.requests import Request
    from sqlmodel import SQLModel, Session, create_engine

    from backend.api.players import get_leaderboard
    from backend.consts import DEFAULT_SIGMA
    from backend.db.models import CurrentPlayerRank, Game, Player, Team
    from backend.settings import settings
except ModuleNotFoundError:
    Request = None
    SQLModel = None
    Session = None
    create_engine = None
    get_leaderboard = None
    DEFAULT_SIGMA = None
    CurrentPlayerRank = None
    Game = None
    Player = None
    Team = None
    settings = None


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/players/leaderboard",
            "headers": [],
            "client": ("203.0.113.10", 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


@unittest.skipIf(
    SQLModel is None or Session is None or get_leaderboard is None,
    "Project dependencies are missing",
)
class LeaderboardInactivePlayersTests(unittest.TestCase):
    def test_overall_leaderboard_includes_inactive_players(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            now = dt.datetime.now(tz=settings.tz)
            active = Player(player_name="Alice", player_color="#f00", active=True)
            inactive = Player(player_name="Bob", player_color="#00f", active=False)
            session.add_all([active, inactive])
            session.flush()

            session.add_all(
                [
                    CurrentPlayerRank(
                        player_id=active.id,
                        mu_overall=1010.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=1010.0,
                        sigma_monthly=float(DEFAULT_SIGMA),
                        mu_yearly=1010.0,
                        sigma_yearly=float(DEFAULT_SIGMA),
                        last_updated=now,
                    ),
                    CurrentPlayerRank(
                        player_id=inactive.id,
                        mu_overall=990.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=990.0,
                        sigma_monthly=float(DEFAULT_SIGMA),
                        mu_yearly=990.0,
                        sigma_yearly=float(DEFAULT_SIGMA),
                        last_updated=now,
                    ),
                ]
            )

            game = Game(game_timestamp=now, result_team1=10, result_team2=8)
            session.add(game)
            session.flush()
            session.add_all(
                [
                    Team(game_id=game.id, player_id=active.id, team_number=1),
                    Team(game_id=game.id, player_id=inactive.id, team_number=2),
                ]
            )
            session.commit()

            overall = get_leaderboard(
                make_request(),
                leaderboard_type="overall",
                session=session,
            )
            yearly = get_leaderboard(
                make_request(),
                leaderboard_type="yearly",
                year=now.year,
                session=session,
            )

        self.assertEqual({row.player_name for row in overall}, {"Alice", "Bob"})
        self.assertEqual({row.player_name for row in yearly}, {"Alice"})
        self.assertFalse(next(row for row in overall if row.player_name == "Bob").active)


if __name__ == "__main__":
    unittest.main()
