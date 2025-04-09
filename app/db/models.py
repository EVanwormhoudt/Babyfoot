import datetime
from dataclasses import dataclass
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class Player(SQLModel, table=True):
    """
    Represents a player in the system.

    Attributes:
        id (int): Unique identifier for the player.
        player_name (str): Name of the player.
        player_color (str): Color associated with the player.
        active (int): Indicates whether the player is active.
        rating_history (List[PlayerRatingHistory]): Historical ratings of the player.
        rating (CurrentPlayerRank): Current ranking of the player.
    """
    __tablename__ = "players"
    id: Optional[int] = Field(default=None, primary_key=True)
    player_name: str
    player_color: str
    active: int
    rating_history: Optional[List["PlayerRatingHistory"]] = Relationship(back_populates="player")
    rating: "CurrentPlayerRank" = Relationship(back_populates="player", sa_relationship_kwargs={"uselist": False})


class PlayerRatingHistory(SQLModel, table=True):
    """
    Stores the rating history of players.

    Attributes:
        update_id (int): Unique identifier for the rating update.
        player_id (int): Identifier of the player.
        mu (int): Mean rating value.
        sigma (int): Standard deviation of the rating.
        date (datetime.date): Date of the rating update.
        rank (int): Player's rank at the time of update.
        rank_type (str): Type of ranking (e.g., monthly, yearly).
    """
    __tablename__ = "players_rating_history"
    update_id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id")
    mu: Optional[float]
    sigma: Optional[float]
    date: datetime.date
    rank: int
    rank_type: str
    player: Optional[Player] = Relationship(back_populates="rating_history")


class Game(SQLModel, table=True):
    """
    Represents a game played between teams.

    Attributes:
        id (int): Unique identifier for the game.
        game_date (datetime.date): Date the game was played.
        game_time (str): Time the game was played.
        result_team1 (int): Score/result of team 1.
        result_team2 (int): Score/result of team 2.
        teams (List[Team]): Teams participating in the game.
    """
    __tablename__ = "games"
    id: Optional[int] = Field(default=None, primary_key=True)
    game_date: datetime.date
    game_time: str
    result_team1: int
    result_team2: int
    teams: List["Team"] = Relationship(back_populates="game")

    class Config:
        arbitrary_types_allowed = True


class Team(SQLModel, table=True):
    """
    Represents a team in a game.

    Attributes:
        id (int): Unique identifier for the team.
        game_id (int): Identifier of the game the team is participating in.
        player_name (str): Name of the player in the team.
        team_number (int): Team number.
    """
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="games.id")
    player_name: str
    team_number: int
    game: Optional[Game] = Relationship(back_populates="teams")

    class Config:
        arbitrary_types_allowed = True


class CurrentPlayerRank(SQLModel, table=True):
    """
    Represents the current ranking of a player.

    Attributes:
        player_id (int): Identifier of the player.
        mu_overall (float): Overall mean rating.
        sigma_overall (float): Overall standard deviation of rating.
        mu_monthly (float): Monthly mean rating.
        sigma_monthly (float): Monthly standard deviation.
        mu_yearly (float): Yearly mean rating.
        sigma_yearly (float): Yearly standard deviation.
        last_updated (datetime.datetime): Last update timestamp.
    """
    __tablename__ = "current_player_rank"
    player_id: int = Field(default=None, primary_key=True, foreign_key="players.id")
    mu_overall: float
    sigma_overall: float
    mu_monthly: float
    sigma_monthly: float
    mu_yearly: float
    sigma_yearly: float
    last_updated: datetime.datetime
    player: Optional[Player] = Relationship(back_populates="rating")

    class Config:
        arbitrary_types_allowed = True

    def get_mu(self, rating_type):
        match rating_type:
            case "monthly":
                return self.mu_monthly
            case "yearly":
                return self.mu_yearly
            case "overall":
                return self.mu_overall

    def get_sigma(self, rating_type):
        match rating_type:
            case "monthly":
                return self.sigma_monthly
            case "yearly":
                return self.sigma_yearly
            case "overall":
                return self.sigma_overall

    def set_mu(self, rating_type, value):
        match rating_type:
            case "monthly":
                self.mu_monthly = value
            case "yearly":
                self.mu_yearly = value
            case "overall":
                self.mu_overall = value

    def set_sigma(self, rating_type, value):
        match rating_type:
            case "monthly":
                self.sigma_monthly = value
            case "yearly":
                self.sigma_yearly = value
            case "overall":
                self.sigma_overall = value


@dataclass
class Rating:
    """
    Represents a rating with its name, mean, and standard deviation.

    Attributes:
        name (str): Name of the rating.
        mu (float): Mean rating value.
        sigma (float): Standard deviation of the rating.
    """
    name: str
    mu: float
    sigma: float
