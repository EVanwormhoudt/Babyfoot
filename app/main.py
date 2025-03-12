from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import List, Optional, Annotated

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlmodel import select

from .db import get_session, init_db
from .db.models import Game, Player, PlayerRatingHistory, CurrentPlayerRank, Team


# Initialize FastAPI app


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

SessionDep = Annotated[Session, Depends(get_session)]


class TeamResponse(BaseModel):
    id: int
    player_name: str
    team_number: int


class GameResponse(BaseModel):
    id: int
    game_date: datetime.date
    game_time: str
    result_team1: int
    result_team2: int
    teams: List[TeamResponse]


class PlayerResponse(BaseModel):
    id: int
    player_name: str
    last_rank: Optional[float]  # Include `last_rank` for the response

    class Config:
        orm_mode = True


@app.get("/games", response_model=List[GameResponse])
def get_games(session: Session = Depends(get_session)) -> List[GameResponse]:
    games = session.execute(
        select(Game).options(selectinload(Game.teams))
    ).scalars().all()

    return games


@app.get("/players", response_model=List[PlayerResponse])
def get_players_with_rank(session: Session = Depends(get_session)):
    query = (
        select(Player)
        .join(CurrentPlayerRank, Player.id == CurrentPlayerRank.player_id)
    )
    results = session.execute(query).all()

    # Transform the results into PlayerResponse objects

    return results


@app.post("/api/players", response_model=Player)
def create_player(player: Player):
    pass


@app.get("/api/players/{player_id}", response_model=Player)
def get_player(player_id: int):
    pass  # Retrieve player


@app.get("/api/players", response_model=List[Player])
def list_players(active: Optional[int] = None):
    pass


@app.put("/api/players/{player_id}", response_model=Player)
def update_player(player_id: int, player: Player):
    pass


@app.delete("/api/players/{player_id}")
def delete_player(player_id: int):
    pass


# --- Games ---
@app.post("/api/games", response_model=Game)
def create_game(game: Game):
    pass


@app.get("/api/games/{game_id}", response_model=Game)
def get_game(game_id: int):
    pass


@app.get("/api/games", response_model=List[Game])
def list_games(player_name: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None):
    pass


@app.put("/api/games/{game_id}", response_model=Game)
def update_game(game_id: int, game: Game):
    pass


@app.delete("/api/games/{game_id}")
def delete_game(game_id: int):
    pass


# --- Rankings ---
@app.get("/api/rankings", response_model=List[CurrentPlayerRank])
def get_rankings(rank_type: str = "overall"):
    pass


# --- Player Statistics ---
@app.get("/api/players/{player_id}/stats")
def player_stats(player_id: int, rank_type: str = "overall"):
    pass


# --- Player Rating History ---
@app.get("/api/players/{player_id}/ratings", response_model=List[PlayerRatingHistory])
def player_rating_history(player_id: int, rank_type: Optional[str] = None):
    pass


# --- Teams ---
@app.post("/api/teams", response_model=Team)
def create_team(team: Team):
    pass


@app.get("/api/teams/{team_id}", response_model=Team)
def get_team(team_id: int):
    pass


@app.get("/api/teams", response_model=List[Team])
def list_teams():
    pass


@app.put("/api/teams/{team_id}", response_model=Team)
def update_team(team_id: int, team: Team):
    pass


@app.delete("/api/teams/{team_id}")
def delete_team(team_id: int):
    pass
