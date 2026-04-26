import datetime as dt
import unittest

try:
    from sqlalchemy.orm import selectinload
    from sqlmodel import SQLModel, Session, create_engine, select

    from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
    from backend.db.models import Game, Player, PlayerRatingHistory, Team
    from backend.database_setup.rebuild_ratings_and_history import rebuild_all_ratings_and_history
except ModuleNotFoundError:
    SQLModel = None
    Session = None
    create_engine = None
    select = None
    selectinload = None
    DEFAULT_RATING = None
    DEFAULT_SIGMA = None
    Game = None
    Player = None
    PlayerRatingHistory = None
    Team = None
    rebuild_all_ratings_and_history = None


@unittest.skipIf(
    SQLModel is None or Session is None or rebuild_all_ratings_and_history is None,
    "Project dependencies are missing",
)
class RebuildRatingHistoryTests(unittest.TestCase):
    def test_monthly_and_yearly_history_are_daily_and_changed_only(self):
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

            game_specs = [
                (dt.datetime(2025, 12, 31, 20, 0, tzinfo=dt.timezone.utc), 10, 0),
                (dt.datetime(2026, 1, 10, 20, 0, tzinfo=dt.timezone.utc), 0, 10),
            ]
            for ts, result_team1, result_team2 in game_specs:
                game = Game(
                    game_timestamp=ts,
                    result_team1=result_team1,
                    result_team2=result_team2,
                )
                session.add(game)
                session.flush()
                session.add(Team(game_id=game.id, player_id=players[0].id, team_number=1))
                session.add(Team(game_id=game.id, player_id=players[1].id, team_number=2))

            session.flush()
            stats = rebuild_all_ratings_and_history(session)
            session.commit()

            history_rows = session.exec(
                select(PlayerRatingHistory)
                .where(PlayerRatingHistory.player_id == players[0].id)
                .order_by(PlayerRatingHistory.rank_type.asc(), PlayerRatingHistory.date.asc())
            ).all()

        rows_by_type = {
            "overall": [],
            "monthly": [],
            "yearly": [],
        }
        for row in history_rows:
            rows_by_type[row.rank_type].append(row)

        self.assertEqual([row.date for row in rows_by_type["overall"]], [
            dt.date(2025, 12, 31),
            dt.date(2026, 1, 10),
        ])
        self.assertEqual([row.date for row in rows_by_type["monthly"]], [
            dt.date(2025, 12, 31),
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 10),
        ])
        self.assertEqual([row.date for row in rows_by_type["yearly"]], [
            dt.date(2025, 12, 31),
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 10),
        ])

        monthly_reset_row = rows_by_type["monthly"][1]
        yearly_reset_row = rows_by_type["yearly"][1]
        self.assertEqual(monthly_reset_row.mu, float(DEFAULT_RATING))
        self.assertEqual(monthly_reset_row.sigma, float(DEFAULT_SIGMA))
        self.assertEqual(yearly_reset_row.mu, float(DEFAULT_RATING))
        self.assertEqual(yearly_reset_row.sigma, float(DEFAULT_SIGMA))

        self.assertEqual(stats.history_overall_rows, 4)
        self.assertEqual(stats.history_monthly_rows, 6)
        self.assertEqual(stats.history_yearly_rows, 6)


if __name__ == "__main__":
    unittest.main()
