# from openskill.models import BradleyTerryFull
from openskill.models import BradleyTerryFull

from ..db.models import Game, Player, Rating


def calculate_new_scores(
        game: Game,
        team1: list[Player],
        team2: list[Player]
):
    model = BradleyTerryFull(margin=2)
    scores = {}
    for rating_type in ["overall", "monthly", "yearly"]:
        # Dynamically construct the attribute names for mu and sigma

        result = [game.result_team1, game.result_team2]

        # Use getattr to fetch the attributes dynamically
        team1_ratings = [
            model.rating(player.rating.get_mu(rating_type),
                         player.rating.get_sigma(rating_type),
                         player.player_name)
            for player in team1
        ]
        team2_ratings = [
            model.rating(player.rating.get_mu(rating_type),
                         player.rating.get_sigma(rating_type),
                         player.player_name)
            for player in team2]

        team1_scored, team2_scored = model.rate([team1_ratings, team2_ratings], scores=result)
        scores[rating_type] = [Rating(player.player_name, rating.sigma, rating.mu)
                               for player, rating in zip(team1 + team2, team1_scored + team2_scored)]

    return scores
