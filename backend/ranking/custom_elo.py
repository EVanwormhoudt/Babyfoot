import datetime
import math
from typing import List

from ..db.models import Game, Player, CurrentPlayerRank


# Assuming you have imported your models:
# Player, PlayerRatingHistory, Game, CurrentPlayerRank, etc.
# And that each CurrentPlayerRank has methods get_mu(), set_mu(), get_sigma(), set_sigma().


# Assume your models have been imported:
#   Player, PlayerRatingHistory, Game, CurrentPlayerRank, etc.
#
# The CurrentPlayerRank is assumed to have the methods:
#    get_mu(rating_type), set_mu(rating_type, value),
#    get_sigma(rating_type), set_sigma(rating_type, value)

def update_all_ratings(
        game: "Game",  # The game record (has game_date, result_team1, result_team2, K, etc.)
        team1: List["Player"],  # List of players on team 1
        team2: List["Player"],  # List of players on team 2
        rating_types: List[str] = ["overall", "monthly", "yearly"],
        non_linear_scale: float = 10,  # Controls the steepness of the margin multiplier.
        K_sigma: float = 10,  # Constant for sigma updates.
        sigma_min: float = 50,  # Minimum allowed sigma value.
        c_effect: float = 3  # Constant that weights the impact of sigma in the effective rating.
) -> None:
    """
    Updates each player's rating (both mu and sigma) for the specified rating types using:

      1. An Elo-style update for the mean rating (mu) where the expected score is computed
         from an *effective rating*:
            effective = mu - c_effect * sigma
         Thus, the expected score for a player becomes:
            E = 1 / (1 + 10^((opp_effective - current_effective)/400))

      2. A zero-sum adjustment on the mu deltas so that the total change across all players is zero.

      3. A heuristic for sigma that adjusts uncertainty based on performance:
            sigma_delta = K_sigma * margin_multiplier * (|S - E| - 0.5)
         This increases sigma when the result is surprising (|S - E| > 0.5) and decreases it otherwise,
         but sigma will not drop below sigma_min.
    """
    # --- Determine game outcome ---
    if game.result_team1 > game.result_team2:
        s_team1, s_team2 = 1.0, 0.0
    elif game.result_team1 < game.result_team2:
        s_team1, s_team2 = 0.0, 1.0
    else:
        s_team1 = s_team2 = 0.5  # Tie game

    margin = abs(game.result_team1 - game.result_team2)
    margin_multiplier = math.exp(margin / non_linear_scale)
    K = 32  # The base K-factor for mu updates

    for rating_type in rating_types:
        raw_deltas = {}  # Raw changes to mu for each player.
        performance_errors = {}  # Store |S - E| for each player, used for sigma update.

        # --- Process Team 1 players ---
        # Compute the opposing team’s average effective rating.
        if team2:
            opp_effective_team1 = sum(
                (p.rating.get_mu(rating_type) - c_effect * p.rating.get_sigma(rating_type))
                for p in team2
            ) / len(team2)
        else:
            opp_effective_team1 = 0

        for player in team1:
            current_mu = player.rating.get_mu(rating_type)
            current_sigma = player.rating.get_sigma(rating_type)
            current_effective = current_mu - c_effect * current_sigma

            # Compute expected score using effective ratings.
            expected = 1 / (1 + 10 ** ((opp_effective_team1 - current_effective) / 400))
            raw_delta = K * margin_multiplier * (s_team1 - expected)
            raw_deltas[player.id] = raw_delta
            performance_errors[player.id] = abs(s_team1 - expected)

        # --- Process Team 2 players ---
        if team1:
            opp_effective_team2 = sum(
                (p.rating.get_mu(rating_type) - c_effect * p.rating.get_sigma(rating_type))
                for p in team1
            ) / len(team1)
        else:
            opp_effective_team2 = 0

        for player in team2:
            current_mu = player.rating.get_mu(rating_type)
            current_sigma = player.rating.get_sigma(rating_type)
            current_effective = current_mu - c_effect * current_sigma

            expected = 1 / (1 + 10 ** ((opp_effective_team2 - current_effective) / 400))
            raw_delta = K * margin_multiplier * (s_team2 - expected)
            raw_deltas[player.id] = raw_delta
            performance_errors[player.id] = abs(s_team2 - expected)

        # --- Adjust mu deltas so that the total change is zero (zero-sum update) ---
        all_players = team1 + team2
        total_delta = sum(raw_deltas[p.id] for p in all_players)
        offset = total_delta / len(all_players)
        print(f"\nUpdating {rating_type} ratings:")
        print(f"  Total raw delta: {total_delta:.2f}, Offset: {offset:.2f}")

        # --- Apply adjusted mu delta and update sigma ---
        for player in all_players:
            final_delta = raw_deltas[player.id] - offset
            current_mu = player.rating.get_mu(rating_type)
            new_mu = current_mu + final_delta
            player.rating.set_mu(rating_type, new_mu)

            # Update sigma based on performance error.
            current_sigma = player.rating.get_sigma(rating_type)
            perf_error = performance_errors[player.id]
            sigma_delta = K_sigma * margin_multiplier * (perf_error - 0.5)
            new_sigma = max(sigma_min, current_sigma + sigma_delta)
            player.rating.set_sigma(rating_type, new_sigma)

            player.rating.last_updated = datetime.datetime.now()

            print(
                f"  Player {player.player_name} ({rating_type}): "
                f"raw_delta {raw_deltas[player.id]:+6.2f}, final_delta {final_delta:+6.2f}, "
                f"new mu {new_mu:6.2f}, "
                f"perf_error {perf_error:.2f}, sigma_delta {sigma_delta:+6.2f}, new sigma {new_sigma:6.2f}"
            )


# --- Demonstration: A 2v2 Match ---

if __name__ == "__main__":
    # Create four players.
    alice = Player(id=1, player_name="Alice", player_color="red", active=1)
    bob = Player(id=2, player_name="Bob", player_color="blue", active=1)
    charlie = Player(id=3, player_name="Charlie", player_color="green", active=1)
    david = Player(id=4, player_name="David", player_color="yellow", active=1)

    now = datetime.datetime.now()
    # Initialize each player's current rating (mu and sigma for each type).
    alice.rating = CurrentPlayerRank(
        player_id=1,
        mu_overall=1600, sigma_overall=100,
        mu_monthly=1600, sigma_monthly=200,
        mu_yearly=1600, sigma_yearly=300,
        last_updated=now
    )
    bob.rating = CurrentPlayerRank(
        player_id=2,
        mu_overall=1600, sigma_overall=200,
        mu_monthly=1600, sigma_monthly=200,
        mu_yearly=1600, sigma_yearly=200,
        last_updated=now
    )
    charlie.rating = CurrentPlayerRank(
        player_id=3,
        mu_overall=1500, sigma_overall=200,
        mu_monthly=1500, sigma_monthly=200,
        mu_yearly=1500, sigma_yearly=200,
        last_updated=now
    )
    david.rating = CurrentPlayerRank(
        player_id=4,
        mu_overall=1500, sigma_overall=200,
        mu_monthly=1500, sigma_monthly=200,
        mu_yearly=1500, sigma_yearly=200,
        last_updated=now
    )

    # Initialize empty rating history lists.
    alice.rating_history = []
    bob.rating_history = []
    charlie.rating_history = []
    david.rating_history = []

    # Create a game: For example, Team 1 wins 10–5.
    game_date = datetime.date.today()
    game = Game(
        id=1,
        game_date=game_date,
        game_time="20:00",
        result_team1=10,
        result_team2=5,
        teams=[]
    )
    # Set the base K-factor for mu updates.

    # Define teams.
    team1 = [alice, bob]  # Team 1: Alice and Bob.
    team2 = [charlie, david]  # Team 2: Charlie and David.

    # Perform the rating updates (overall, monthly, yearly).
    update_all_ratings(game, team1, team2)

    # Display final ratings.
    print("\nFinal Ratings:")
    for player in [alice, bob, charlie, david]:
        print(
            f"{player.player_name}: overall = {player.rating.mu_overall:.2f} (σ={player.rating.sigma_overall:.2f}), "
            f"monthly = {player.rating.mu_monthly:.2f} (σ={player.rating.sigma_monthly:.2f}), "
            f"yearly = {player.rating.mu_yearly:.2f} (σ={player.rating.sigma_yearly:.2f})"
        )
