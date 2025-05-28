from collections import defaultdict

import psycopg2
from sqlalchemy.orm import selectinload
from sqlmodel import select

from app.db.database import get_session
from app.db.models import Game, Player
from app.ranking.custom_elo import calculate_new_scores

conn = psycopg2.connect(
    dbname="babyfoot",
    host="localhost",
    port="5432"
)


def find_player(player: Player, name):
    if player.player_name == name:
        return 1
    return 0


fetch_query = "SELECT * FROM games JOIN public.teams t on games.id = t.game_id"

games: list[Game] = next(get_session()).execute(
    select(Game).options(selectinload(Game.teams))
).scalars().all()

players: list[Player] = next(get_session()).execute(
    select(Player).options(selectinload(Player.rating))
).scalars().all()

players_dict = {player.player_name: player for player in players}

for game in games:
    teams = defaultdict(list)
    for player in game.teams:
        teams[player.team_number] += [players_dict[player.player_name]]

    result = calculate_new_scores(game, teams[1], teams[2])
    for rating_type in ["overall", "monthly", "yearly"]:
        for rating in result[rating_type]:
            players_dict[rating.name].rating.set_mu(rating_type, rating.mu)
            players_dict[rating.name].rating.set_sigma(rating_type, rating.sigma)

            if "Bertrand" == rating.name:
                print(rating)
                break
for key, value in players_dict.items():
    print(key)
    print(value.rating)
