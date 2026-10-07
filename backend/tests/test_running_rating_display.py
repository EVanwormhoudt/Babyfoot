import datetime as dt
import unittest

from sqlmodel import SQLModel, Session, create_engine, select
from starlette.requests import Request

from backend.api.games import get_game, get_games
from backend.db.models import Game, GamePlayerRatingChange, Player, Team
from backend.ranking.custom_elo import recalculate_all_ratings
from backend.settings import settings


class RunningRatingDisplayTests(unittest.TestCase):
    def test_running_ratings_include_matches_outside_page_and_reset_each_day(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1234)})

        with Session(engine) as session:
            alice = Player(player_name="Alice", player_color="#f00", active=True)
            bob = Player(player_name="Bob", player_color="#00f", active=True)
            session.add_all([alice, bob])
            session.flush()
            start = dt.datetime(2026, 3, 18, 10, tzinfo=settings.tz)
            games = []
            # Equal timestamps use game ID to order the displayed transitions.
            for timestamp in (start, start, start + dt.timedelta(days=1)):
                game = Game(game_timestamp=timestamp, result_team1=10, result_team2=0)
                session.add(game)
                session.flush()
                session.add_all([
                    Team(game_id=game.id, player_id=alice.id, team_number=1),
                    Team(game_id=game.id, player_id=bob.id, team_number=2),
                ])
                games.append(game)
            session.flush()
            recalculate_all_ratings(session)
            session.commit()

            page = get_games(
                request, session=session, scope="all", limit=1, offset=1,
                start_date=None, end_date=None, player_id=alice.id,
            )
            self.assertEqual(page["items"][0].id, games[1].id)
            detail = get_game(games[1].id, request, session=session)
            for response in (page["items"][0], detail):
                for change in response.rating_changes:
                    if change.player_id == alice.id:
                        self.assertEqual(change.mu_before, 1000.0)
                        self.assertEqual(change.mu_after, 1016.0)
                        self.assertEqual(change.running_mu_before, 1016.0)
                        self.assertEqual(change.running_mu_after, 1032.0)
                        self.assertEqual(change.delta_mu, 16.0)
                    else:
                        self.assertEqual(change.running_mu_before, 984.0)
                        self.assertEqual(change.running_mu_after, 968.0)

            next_day = get_game(games[2].id, request, session=session)
            for change in next_day.rating_changes:
                self.assertEqual(change.running_mu_before, change.mu_before)
                self.assertEqual(change.running_mu_after, change.mu_after)
                self.assertEqual(change.mu_before, 1032.0 if change.player_id == alice.id else 968.0)

            # Display enrichment never rewrites the stored calculation inputs.
            stored = session.exec(
                select(GamePlayerRatingChange).where(
                    GamePlayerRatingChange.game_id == games[1].id,
                    GamePlayerRatingChange.player_id == alice.id,
                )
            ).all()
            self.assertTrue(stored)
            self.assertTrue(all(change.mu_before == 1000.0 for change in stored))


if __name__ == "__main__":
    unittest.main()
