from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import router as api_router
from .database_setup.seed_if_empty import populate_if_empty
from .db.session import init_db
from .jobs import (
    snapshot_daily_ratings_and_roll_periods,
)
from .settings import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone=settings.tz)


def _log_scheduler_event(event) -> None:
    if getattr(event, "exception", None) is not None:
        logger.error("Scheduled job %s failed\n%s", event.job_id, event.traceback)
        return

    if event.code == EVENT_JOB_MISSED:
        logger.warning("Scheduled job %s was missed", event.job_id)
        return

    logger.info("Scheduled job %s completed", event.job_id)



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    populate_if_empty()
    scheduler.add_listener(_log_scheduler_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    scheduler.add_job(
        snapshot_daily_ratings_and_roll_periods,
        CronTrigger(hour=0, minute=5, timezone=settings.tz),
        id="snapshot_daily_ratings_and_roll_periods",
        replace_existing=True,
    )
    scheduler.start()
    for job in scheduler.get_jobs():
        logger.info("Scheduled job %s next run at %s", job.id, job.next_run_time)
    try:
        yield
    finally:
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
