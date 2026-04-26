import datetime as dt
import unittest

try:
    from sqlmodel import SQLModel, Session, create_engine

    from backend.api.games import _validate_game_payload
    from backend.db.models import CurrentPlayerRank, Player, PlayerRatingHistory
    from backend.schemas import GameCreate, TeamCreate
except ModuleNotFoundError:
    SQLModel = None
    Session = None
    create_engine = None
    _validate_game_payload = None
    CurrentPlayerRank = None
    Player = None
    PlayerRatingHistory = None
    GameCreate = None
    TeamCreate = None


@unittest.skipIf(
    SQLModel is None or Session is None or _validate_game_payload is None,
    "Project dependencies are missing",
)
class GamePayloadValidationTests(unittest.TestCase):
    def test_loads_current_rating_and_latest_saved_ratings_by_type(self):
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

            now = dt.datetime(2026, 4, 26, 12, 0, tzinfo=dt.timezone.utc)
            session.add(
                CurrentPlayerRank(
                    player_id=players[0].id,
                    mu_overall=1020.0,
                    sigma_overall=390.0,
                    mu_monthly=1010.0,
                    sigma_monthly=391.0,
                    mu_yearly=1015.0,
                    sigma_yearly=392.0,
                    last_updated=now,
                )
            )
            session.add(
                CurrentPlayerRank(
                    player_id=players[1].id,
                    mu_overall=980.0,
                    sigma_overall=405.0,
                    mu_monthly=985.0,
                    sigma_monthly=404.0,
                    mu_yearly=990.0,
                    sigma_yearly=403.0,
                    last_updated=now,
                )
            )

            session.add_all(
                [
                    PlayerRatingHistory(
                        player_id=players[0].id,
                        mu=1000.0,
                        sigma=400.0,
                        date=dt.date(2026, 4, 10),
                        rank=2,
                        rank_type="overall",
                    ),
                    PlayerRatingHistory(
                        player_id=players[0].id,
                        mu=1008.0,
                        sigma=398.0,
                        date=dt.date(2026, 4, 20),
                        rank=1,
                        rank_type="overall",
                    ),
                    PlayerRatingHistory(
                        player_id=players[0].id,
                        mu=1012.0,
                        sigma=397.0,
                        date=dt.date(2026, 4, 25),
                        rank=1,
                        rank_type="monthly",
                    ),
                    PlayerRatingHistory(
                        player_id=players[0].id,
                        mu=1004.0,
                        sigma=399.0,
                        date=dt.date(2026, 4, 15),
                        rank=2,
                        rank_type="monthly",
                    ),
                    PlayerRatingHistory(
                        player_id=players[0].id,
                        mu=1006.0,
                        sigma=396.0,
                        date=dt.date(2026, 1, 31),
                        rank=1,
                        rank_type="yearly",
                    ),
                    PlayerRatingHistory(
                        player_id=players[1].id,
                        mu=990.0,
                        sigma=402.0,
                        date=dt.date(2026, 4, 18),
                        rank=3,
                        rank_type="overall",
                    ),
                    PlayerRatingHistory(
                        player_id=players[1].id,
                        mu=995.0,
                        sigma=401.0,
                        date=dt.date(2026, 4, 19),
                        rank=2,
                        rank_type="monthly",
                    ),
                ]
            )
            session.commit()

            payload = GameCreate(
                result_team1=10,
                result_team2=8,
                teams=[
                    TeamCreate(player_id=players[0].id, team_number=1),
                    TeamCreate(player_id=players[1].id, team_number=2),
                ],
            )

            players_by_id = _validate_game_payload(payload, session)
            alice = players_by_id[players[0].id]
            bob = players_by_id[players[1].id]

            self.assertEqual(alice.rating.mu_overall, 1020.0)
            self.assertEqual(set(alice.latest_saved_ratings.keys()), {"overall", "yearly", "monthly"})
            self.assertEqual(alice.latest_saved_rating.rank_type, "overall")
            self.assertEqual(alice.latest_saved_rating.date, dt.date(2026, 4, 20))
            self.assertEqual(alice.latest_saved_rating.mu, 1008.0)
            self.assertEqual(alice.latest_saved_ratings["monthly"].date, dt.date(2026, 4, 25))
            self.assertEqual(alice.latest_saved_ratings["monthly"].mu, 1012.0)
            self.assertEqual(alice.latest_saved_ratings["yearly"].date, dt.date(2026, 1, 31))
            self.assertEqual(alice.latest_saved_ratings["yearly"].mu, 1006.0)
            self.assertIs(alice.latest_saved_rating_overall, alice.latest_saved_ratings["overall"])
            self.assertIs(alice.latest_saved_rating_annual, alice.latest_saved_ratings["yearly"])
            self.assertIs(alice.latest_saved_rating_monthly, alice.latest_saved_ratings["monthly"])

            self.assertEqual(bob.rating.mu_overall, 980.0)
            self.assertEqual(bob.latest_saved_rating.rank_type, "overall")
            self.assertEqual(bob.latest_saved_rating.date, dt.date(2026, 4, 18))
            self.assertEqual(bob.latest_saved_rating.mu, 990.0)
            self.assertEqual(bob.latest_saved_ratings["monthly"].date, dt.date(2026, 4, 19))
            self.assertEqual(bob.latest_saved_ratings["monthly"].mu, 995.0)
            self.assertIsNone(bob.latest_saved_ratings["yearly"])
            self.assertIsNone(bob.latest_saved_rating_annual)


if __name__ == "__main__":
    unittest.main()
