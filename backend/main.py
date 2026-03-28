from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import router as api_router
from .database_setup.seed_if_empty import populate_if_empty
from .db.session import init_db
from .jobs import (
    snapshot_and_reset_monthly,
    snapshot_and_reset_yearly,
    snapshot_overall_daily_if_changed,
)
from .settings import settings

scheduler = BackgroundScheduler()



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    populate_if_empty()
    scheduler.add_job(snapshot_overall_daily_if_changed, CronTrigger(hour=0, minute=5))
    scheduler.add_job(snapshot_and_reset_monthly, CronTrigger(day="1", hour=0, minute=0))
    scheduler.add_job(snapshot_and_reset_yearly, CronTrigger(month="1", day="1", hour=0, minute=0))
    scheduler.start()
    try:
        yield
    finally:
        # ---- shutdown ----
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan, title="Foosball Ratings API", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Foosball Ratings API",
        "health": "/healthz",
        "docs": "/docs",
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
