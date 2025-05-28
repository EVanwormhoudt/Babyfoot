from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Annotated, Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from sqlmodel import select, Session
from starlette.middleware.cors import CORSMiddleware

from .consts import DEFAULT_RATING, DEFAULT_SIGMA
from .db import get_session, init_db
from .db.models import Game, Player, CurrentPlayerRank, Team
from .utils import get_scope_date, get_basic_stats, get_teammate_stats, get_win_streaks


# Initialize FastAPI app


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # or ["*"] for dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_session)]


class PlayerCreate(BaseModel):
    player_name: str
    player_color: str


class PlayerRead(PlayerCreate):
    id: int
    rating: CurrentPlayerRank
    active: bool


class PlayerUpdate(BaseModel):
    player_name: str
    player_color: str
    active: bool


class TeamCreate(BaseModel):
    player_id: int
    team_number: int


class GameCreate(BaseModel):
    result_team1: int
    result_team2: int
    teams: List[TeamCreate]


class GameUpdate(BaseModel):
    result_team1: int
    result_team2: int


class GameRead(GameCreate):
    id: int
    game_timestamp: datetime


@app.post("/api/players", response_model=PlayerRead)
def create_player(player: PlayerCreate, session: Session = Depends(get_session)):
    new_player = Player(active=True, **player.model_dump())
    # Check if the player already exists
    existing_player = session.exec(
        select(Player).where(Player.player_name == new_player.player_name)
    ).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Player already exists")
    session.add(new_player)
    session.commit()
    session.refresh(new_player)
    # Initialize the player's rating
    new_player.rating = CurrentPlayerRank(
        player_id=new_player.id,
        mu_overall=DEFAULT_RATING,
        sigma_overall=DEFAULT_SIGMA,
        mu_monthly=DEFAULT_RATING,
        sigma_monthly=DEFAULT_SIGMA,
        mu_yearly=DEFAULT_RATING,
        sigma_yearly=DEFAULT_SIGMA,
        last_updated=datetime.now()
    )
    session.add(new_player.rating)
    session.commit()

    return new_player


@app.get("/api/players/{player_id}", response_model=PlayerRead)
def get_player(player_id: int, session: Session = Depends(get_session)):
    # fetch the ranking and the player

    player = session.exec(
        select(Player).where(Player.id == player_id).options(selectinload(Player.rating))
    ).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@app.get("/api/players", response_model=List[PlayerRead])
def list_players(session: Session = Depends(get_session)):
    #also fetch the ranking
    players = session.exec(select(Player)).all()
    return players


@app.put("/api/players/{player_id}", response_model=PlayerUpdate)
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


@app.get("/api/players", response_model=List[PlayerRead])
def get_players_with_rank(session: Session = Depends(get_session)):
    query = select(Player).join(CurrentPlayerRank, Player.id == CurrentPlayerRank.player_id)
    results = session.exec(query).all()
    return results


# --- Games ---
@app.get("/api/games", response_model=List[GameRead])
def get_games(
        session: Session = Depends(get_session),
        scope: Optional[str] = Query("all", enum=["all", "monthly"]),
        limit: int = Query(10, ge=1),
        offset: int = Query(0, ge=0),
) -> List[GameRead]:
    stmt = select(Game).options(selectinload(Game.teams))

    # Apply monthly filter
    if scope == "monthly":
        now = datetime.now(tz=ZoneInfo("Europe/Paris"))
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(Game.game_timestamp >= first_of_month)

    # Add pagination
    stmt = stmt.order_by(Game.game_timestamp.desc()).offset(offset).limit(limit)

    games = session.exec(stmt).all()
    return games


@app.post("/api/games", response_model=GameRead)
def create_game(game: GameCreate, session: Session = Depends(get_session)):
    time = datetime.now(ZoneInfo("Europe/Paris"))

    new_game = Game(
        game_timestamp=time,
        result_team1=game.result_team1,
        result_team2=game.result_team2,
    )
    session.add(new_game)
    session.commit()
    session.refresh(new_game)
    for team in game.teams:
        new_team = Team(
            player_id=team.player_id,
            team_number=team.team_number,
            game_id=new_game.id
        )
        session.add(new_team)
    return new_game


@app.get("/api/games/{game_id}", response_model=GameRead)
def get_game(game_id: int, session: Session = Depends(get_session)) -> GameRead:
    game = session.exec(
        select(Game).where(Game.id == game_id).options(selectinload(Game.teams))
    ).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.put("/api/games/{game_id}", response_model=GameRead)
def update_game(game_id: int, game: GameUpdate, session: Session = Depends(get_session)):
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


# Mix
@app.get("/api/players/{player_id}/history", response_model=List[GameRead])
def get_player_games(player_id: int, session: Session = Depends(get_session)):
    games = session.exec(
        select(Game)
        .join(Team, Team.game_id == Game.id)
        .where(Team.player_id == player_id)  # or Team.player_id if you have a foreign key
    ).all()
    if not games:
        raise HTTPException(status_code=404, detail="Player not found")
    return games


@app.get("/api/players/leaderboard/", response_model=List[Player])
def get_leaderboard(session: Session = Depends(get_session),
                    leaderboard_type: Literal["monthly", "yearly", "overall"] = "monthly"
                    ) -> List[Player]:
    # only select player with active = true
    players = session.exec(
        select(Player)
        .where(Player.active == True)
        .options(selectinload(Player.rating))
    ).all()
    players.sort(key=lambda x: getattr(x.rating, f"mu_{leaderboard_type}"), reverse=True)
    return players


@app.get("/api/players/{player_id}/stats")
def get_player_stats(player_id: int, scope: str = "overall", session: Session = Depends(get_session)):
    date_filter = get_scope_date(scope)

    basic = get_basic_stats(session, player_id, date_filter)
    teammates = get_teammate_stats(session, player_id, date_filter)
    streaks = get_win_streaks(session, player_id, date_filter)

    best = max(teammates, key=lambda x: x["win_rate"], default=None)
    worst = min(teammates, key=lambda x: x["win_rate"], default=None)

    return {
        "games_played": basic.games_played,
        "wins": basic.wins,
        "win_rate": basic.wins / basic.games_played if basic.games_played else 0,
        "average_team_score": basic.avg_team_score,
        "average_opponent_score": basic.avg_opponent_score,
        "best_teammate": best,
        "worst_teammate": worst,
        **streaks
    }
