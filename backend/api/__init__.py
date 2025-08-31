from fastapi import APIRouter

from .games import router as games_router
from .players import router as players_router
from .stats import router as stats_router

router = APIRouter()
router.include_router(players_router, prefix="/players", tags=["players"])
router.include_router(games_router, prefix="/games", tags=["games"])
router.include_router(stats_router, prefix="/players", tags=["stats"])
