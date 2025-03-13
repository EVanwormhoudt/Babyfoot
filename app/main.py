from contextlib import asynccontextmanager
from datetime import date
from typing import List, Annotated

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, selectinload
from sqlmodel import select

from .db import get_session, init_db
from .db.models import Game, Player, CurrentPlayerRank


# Initialize FastAPI app


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

SessionDep = Annotated[Session, Depends(get_session)]


class PlayerCreate(BaseModel):
    player_name: str
    player_color: str
    active: int


class PlayerRead(PlayerCreate):
    id: int


class GameCreate(BaseModel):
    game_date: date
    game_time: str
    result_team1: int
    result_team2: int


class GameRead(GameCreate):
    id: int


class TeamCreate(BaseModel):
    game_id: int
    player_name: str
    team_number: int


@app.post("/api/players", response_model=PlayerRead)
def create_player(player: PlayerCreate, session: Session = Depends(get_session)):
    new_player = Player(**player.model_dump())
    session.add(new_player)
    session.commit()
    session.refresh(new_player)
    return new_player


@app.get("/api/players/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, session: Session = Depends(get_session)):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.get("/api/players", response_model=List[PlayerRead])
def list_players(session: Session = Depends(get_session)):
    players = session.exec(select(Player)).all()
    return players


@app.put("/api/players/{player_id}", response_model=PlayerRead)
def update_player(player_id: int, player: PlayerCreate, session: Session = Depends(get_session)):
    existing_player = session.get(Player, player_id)
    if not existing_player:
        raise HTTPException(status_code=404, detail="Player not found")
    for key, value in player.model_dump().items():
        setattr(existing_player, key, value)
    session.commit()
    session.refresh(existing_player)
    return existing_player


@app.delete("/api/players/{player_id}")
def delete_player(player_id: int, session: Session = Depends(get_session)):
    player = session.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    session.delete(player)
    session.commit()
    return {"message": "Player deleted successfully"}


# --- Games ---
@app.get("/api/games", response_model=List[GameRead])
def get_games(session: Session = Depends(get_session)) -> List[GameRead]:
    games = session.exec(select(Game).options(selectinload(Game.teams))).all()
    return games


@app.get("/api/players", response_model=List[PlayerRead])
def get_players_with_rank(session: Session = Depends(get_session)):
    query = select(Player).join(CurrentPlayerRank, Player.id == CurrentPlayerRank.player_id)
    results = session.exec(query).all()
    return results


@app.post("/api/games", response_model=GameRead)
def create_game(game: GameCreate, session: Session = Depends(get_session)):
    new_game = Game(**game.model_dump())
    session.add(new_game)
    session.commit()
    session.refresh(new_game)
    return new_game


@app.get("/api/games/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.put("/api/games/{game_id}", response_model=GameRead)
def update_game(game_id: int, game: GameCreate, session: Session = Depends(get_session)):
    existing_game = session.get(Game, game_id)
    if not existing_game:
        raise HTTPException(status_code=404, detail="Game not found")
    for key, value in game.model_dump().items():
        setattr(existing_game, key, value)
    session.commit()
    session.refresh(existing_game)
    return existing_game


@app.delete("/api/games/{game_id}")
def delete_game(game_id: int, session: Session = Depends(get_session)):
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    session.delete(game)
    session.commit()
    return {"message": "Game deleted successfully"}
