import datetime as dt
import unittest
from unittest.mock import patch

try:
    from sqlalchemy.orm import selectinload
    from sqlmodel import SQLModel, Session, create_engine, select

    from backend.api.games import create_game
    from backend.consts import DEFAULT_RATING, DEFAULT_SIGMA
    from backend.db.models import CurrentPlayerRank, Game, Player
    from backend.period_rollover import ensure_current_period_ratings
    from backend.schemas import GameCreate, TeamCreate
except ModuleNotFoundError:
    SQLModel = None
    Session = None
    create_engine = None
    select = None
    selectinload = None
    create_game = None
    DEFAULT_RATING = None
    DEFAULT_SIGMA = None
    CurrentPlayerRank = None
    Game = None
    Player = None
    ensure_current_period_ratings = None
    GameCreate = None
    TeamCreate = None


@unittest.skipIf(
    SQLModel is None or Session is None or create_game is None or ensure_current_period_ratings is None,
    "Project dependencies are missing",
)
class PeriodRolloverTests(unittest.TestCase):
    def _seed_players(self, session: Session) -> list[Player]:
        players = [
            Player(player_name="Alice", player_color="#f00", active=True),
            Player(player_name="Bob", player_color="#00f", active=True),
        ]
        for player in players:
            session.add(player)
        session.flush()
        return players

    def test_create_game_resets_stale_monthly_ratings_before_first_new_month_game(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        april_ts = dt.datetime(2026, 4, 30, 12, 0, tzinfo=dt.timezone.utc)
        may_ts = dt.datetime(2026, 5, 11, 12, 0, tzinfo=dt.timezone.utc)

        class FixedDateTime(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                if tz is None:
                    return may_ts
                return may_ts.astimezone(tz)

        with Session(engine) as session:
            players = self._seed_players(session)
            session.add_all(
                [
                    CurrentPlayerRank(
                        player_id=players[0].id,
                        mu_overall=1100.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=1100.0,
                        sigma_monthly=390.0,
                        mu_yearly=1100.0,
                        sigma_yearly=390.0,
                        last_updated=april_ts,
                    ),
                    CurrentPlayerRank(
                        player_id=players[1].id,
                        mu_overall=900.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=900.0,
                        sigma_monthly=410.0,
                        mu_yearly=900.0,
                        sigma_yearly=410.0,
                        last_updated=april_ts,
                    ),
                    Game(
                        game_timestamp=april_ts,
                        result_team1=10,
                        result_team2=8,
                    ),
                ]
            )
            session.commit()

            with patch("backend.api.games.datetime", FixedDateTime):
                create_game(
                    GameCreate(
                        result_team1=10,
                        result_team2=0,
                        teams=[
                            TeamCreate(player_id=players[0].id, team_number=1),
                            TeamCreate(player_id=players[1].id, team_number=2),
                        ],
                    ),
                    session,
                )

            refreshed_players = session.exec(
                select(Player)
                .options(selectinload(Player.rating))
                .order_by(Player.id.asc())
            ).all()
            latest_game = session.exec(
                select(Game)
                .options(selectinload(Game.rating_changes))
                .order_by(Game.id.desc())
            ).first()

        self.assertEqual(float(refreshed_players[0].rating.mu_monthly), float(DEFAULT_RATING) + 16.0)
        self.assertEqual(float(refreshed_players[1].rating.mu_monthly), float(DEFAULT_RATING) - 16.0)

        monthly_changes = {
            row.player_id: (float(row.mu_before), float(row.mu_after))
            for row in latest_game.rating_changes
            if row.rating_type == "monthly"
        }
        self.assertEqual(monthly_changes[refreshed_players[0].id], (float(DEFAULT_RATING), float(DEFAULT_RATING) + 16.0))
        self.assertEqual(monthly_changes[refreshed_players[1].id], (float(DEFAULT_RATING), float(DEFAULT_RATING) - 16.0))

    def test_current_month_games_do_not_trigger_another_monthly_reset(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)

        may_game_ts = dt.datetime(2026, 5, 2, 12, 0, tzinfo=dt.timezone.utc)
        now = dt.datetime(2026, 5, 11, 12, 0, tzinfo=dt.timezone.utc)

        with Session(engine) as session:
            players = self._seed_players(session)
            session.add_all(
                [
                    CurrentPlayerRank(
                        player_id=players[0].id,
                        mu_overall=1020.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=1012.0,
                        sigma_monthly=398.0,
                        mu_yearly=1015.0,
                        sigma_yearly=397.0,
                        last_updated=dt.datetime(2026, 4, 30, 12, 0, tzinfo=dt.timezone.utc),
                    ),
                    CurrentPlayerRank(
                        player_id=players[1].id,
                        mu_overall=980.0,
                        sigma_overall=float(DEFAULT_SIGMA),
                        mu_monthly=988.0,
                        sigma_monthly=402.0,
                        mu_yearly=985.0,
                        sigma_yearly=403.0,
                        last_updated=may_game_ts,
                    ),
                    Game(
                        game_timestamp=may_game_ts,
                        result_team1=10,
                        result_team2=8,
                    ),
                ]
            )
            session.commit()

            changed = ensure_current_period_ratings(session, now=now)
            alice_rank = session.get(CurrentPlayerRank, players[0].id)
            bob_rank = session.get(CurrentPlayerRank, players[1].id)
            session.refresh(alice_rank)
            session.refresh(bob_rank)

        self.assertFalse(changed)
        self.assertEqual(float(alice_rank.mu_monthly), 1012.0)
        self.assertEqual(float(bob_rank.mu_monthly), 988.0)


if __name__ == "__main__":
    unittest.main()
