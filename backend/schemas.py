from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict


# ---- Rank ----
class RankRead(BaseModel):
    mu_overall: float
    sigma_overall: float
    mu_monthly: float
    sigma_monthly: float
    mu_yearly: float
    sigma_yearly: float
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)


# ---- Player ----
class PlayerCreate(BaseModel):
    player_name: str
    player_color: str


class PlayerUpdate(BaseModel):
    player_name: str
    player_color: str
    active: bool


class PlayerRead(PlayerCreate):
    id: int
    active: bool
    rating: Optional[RankRead] = None

    model_config = ConfigDict(from_attributes=True)


# ---- Team ----
class TeamCreate(BaseModel):
    player_id: int
    team_number: Literal[1, 2]


class TeamRead(BaseModel):
    player_id: int
    team_number: Literal[1, 2]

    model_config = ConfigDict(from_attributes=True)


# ---- Game ----
class GameCreate(BaseModel):
    result_team1: int
    result_team2: int
    teams: List[TeamCreate]


class GameUpdate(BaseModel):
    result_team1: int
    result_team2: int


class GameRead(BaseModel):
    id: int
    game_timestamp: datetime
    result_team1: int
    result_team2: int
    teams: List[TeamRead]

    model_config = ConfigDict(from_attributes=True)


# ---- Stats ----
class TeammateStat(BaseModel):
    player_id: int
    player_name: str
    games: int
    wins: int
    win_rate: float


class PlayerStats(BaseModel):
    games_played: int
    wins: int
    win_rate: float
    average_team_score: float
    average_opponent_score: float
    best_teammate: Optional[TeammateStat] = None
    worst_teammate: Optional[TeammateStat] = None
    current_win_streak: int
    longest_win_streak: int
