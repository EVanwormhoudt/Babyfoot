# BabyFoot

BabyFoot is a full-stack foosball league tracker for recording matches, ranking players with an Elo-style system, and exploring player statistics over time.

[Live demo](https://babyfoot.chamrai.fr) · [API docs](https://babyfoot.chamrai.fr/docs)

## Screenshots

Add current application screenshots in `docs/screenshots/` and keep these filenames so the README renders them automatically.

![BabyFoot dashboard](docs/screenshots/dashboard.png)

![Leaderboard](docs/screenshots/leaderboard.png)

![Match history](docs/screenshots/match-history.png)

## Features

- Record foosball matches with flexible team composition and score validation.
- Track monthly, yearly, and overall leaderboards.
- Update player ratings with a custom Elo-style ranking system.
- Preserve per-game rating deltas so match history can explain how rankings changed.
- View player statistics including games played, wins, win rate, average scores, teammate performance, streaks, and match history.
- Snapshot rating history daily for historical charts and period-based leaderboards.
- Optionally mask player names for public visitors while allowing trusted users by password, cookie, or IP allowlist.

## Architecture

```mermaid
flowchart LR
    Browser[Browser] --> Nginx[Nginx reverse proxy]
    Nginx --> Frontend[SvelteKit + TypeScript]
    Nginx --> API[FastAPI]
    Frontend --> API
    API --> DB[(PostgreSQL)]
    API --> Scheduler[APScheduler jobs]
    Scheduler --> DB
```

The application is split into four runtime services in Docker Compose:

- `frontend`: SvelteKit and TypeScript UI for dashboards, leaderboards, players, match creation, and match history.
- `fastapi`: FastAPI backend exposing REST endpoints under `/api`.
- `postgres`: PostgreSQL database seeded from `babyfoot.sql` on first container initialization.
- `nginx`: Public entry point that serves the frontend and proxies `/api`, `/docs`, `/redoc`, and health checks to FastAPI.

Name privacy is enforced at the API serialization layer in `backend/privacy.py`, so player, leaderboard, game, and statistics responses can share the same masking rules before data reaches the frontend.

## Ranking System

BabyFoot uses a custom team Elo implementation in `backend/ranking/custom_elo.py`.

Team strength is calculated from the average rating of each team's players. After each match, the backend computes expected win probability, applies a margin-of-victory multiplier, scales the update by team size, and splits the rating delta across teammates. The system maintains separate `overall`, `yearly`, and `monthly` ratings, while storing per-player, per-game rating changes for auditability and UI hover details.

## Statistics And History

The backend exposes player match history, rating history, leaderboard data, and scoped player statistics. Statistics can be filtered by overall, yearly, or monthly periods. Rating history is stored in `players_rating_history`, while immediate current rankings live in `current_player_rank`.

## Scheduled Jobs

FastAPI starts an APScheduler background scheduler during application startup. The job `snapshot_daily_ratings_and_roll_periods` runs every day at 00:05 in the configured timezone, currently `Europe/Paris`. It writes daily rating snapshots for overall, monthly, and yearly rankings when ratings changed, resets monthly ratings on the first day of each month, and resets yearly ratings on January 1.

Startup also calls `ensure_current_period_ratings` so the application catches up if the scheduled rollover was missed while the service was down.

## Technical Decisions And Trade-Offs

- SvelteKit keeps the UI fast and typed while still allowing server-side route loading where it helps hide internal API calls from the browser.
- FastAPI was chosen for a small, explicit REST API with automatic OpenAPI documentation and straightforward request validation.
- PostgreSQL is used instead of a lighter embedded database because ranking history, per-game deltas, and period snapshots benefit from relational constraints and indexed queries.
- Docker Compose keeps local development and deployment close to production by running the frontend, backend, database, and proxy as separate services.
- Nginx centralizes routing so the browser can call the same origin for the UI and API.
- The rating system is intentionally custom rather than a black-box package so match updates can account for foosball-specific behavior such as team games, margin of victory, and monthly/yearly resets.

## Running Locally

Start the complete stack:

```bash
cp .env.example .env
# Edit .env and replace every placeholder secret before using this outside local development.
docker compose up --build
```

Then open:

- Application: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`
- Health check: `http://localhost:8080/healthz`

Database credentials are loaded from `.env`; use `.env.example` as the template and replace the placeholder secrets before running the stack.

## Development

Backend:

```bash
uv sync
uv run uvicorn backend.main:app --reload
```

Frontend:

```bash
cd front-end
npm install
npm run dev
```

Useful environment variables:

- `DATABASE_URL`: SQLAlchemy database URL used by FastAPI.
- `POSTGRES_DB`: PostgreSQL database name used by Docker Compose. Defaults to `babyfoot`.
- `POSTGRES_USER`: PostgreSQL user used by Docker Compose. Defaults to `babyfoot_app`.
- `POSTGRES_PASSWORD`: required PostgreSQL password used by Docker Compose.
- `POSTGRES_PORT`: local host port bound to Postgres. Defaults to `5432` and is bound to `127.0.0.1` only.
- `TIMEZONE`: timezone for rating snapshots and period rollovers.
- `AUTO_POPULATE_IF_EMPTY`: whether the backend should populate an empty database from the configured source.
- `POPULATE_SOURCE_URL`: source URL used by the optional data population flow.
- `NAMES_PRIVACY_PASSWORD`: optional shared password that allows player names to be returned.
- `NAMES_PRIVACY_SESSION_SECRET`: optional signing secret for name-access session cookies. Defaults to `NAMES_PRIVACY_PASSWORD`; set a separate long random value in production.
- `NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS`: optional session lifetime for name-access cookies. Defaults to 30 days.
- `NAMES_VISIBLE_IPS`: optional comma-separated IP/CIDR allowlist that can see player names, for example `192.0.2.10,198.51.100.0/24`.
- `NAMES_TRUSTED_PROXY_IPS`: optional comma-separated IP/CIDR list of reverse proxies whose `X-Real-IP` or `X-Forwarded-For` headers may be trusted for `NAMES_VISIBLE_IPS`.
- `INTERNAL_API_BASE`: server-side API base used by SvelteKit to proxy every browser `/api/...` request to FastAPI.

When either `NAMES_PRIVACY_PASSWORD` or `NAMES_VISIBLE_IPS` is set, player names are replaced with placeholders unless the request comes from an allowlisted IP, includes the password in the `X-Names-Password` header, or has a valid backend-issued `HttpOnly` name-access session cookie. The frontend header includes a key button that posts the password to `/api/privacy/names/session`; the backend validates it and sets a signed cookie that JavaScript cannot read. Forwarded IP headers are ignored unless the immediate peer matches `NAMES_TRUSTED_PROXY_IPS`.

Do not commit `.env`. It is ignored by git. If your Postgres password contains URL-reserved characters, URL-encode it in `DATABASE_URL`.

When Cloudflare Tunnel points at the bundled Nginx service, Nginx accepts
`CF-Connecting-IP` only from loopback or Docker-network peers and forwards that
visitor address to FastAPI. Put real allowed visitor IPs or CIDRs in
`NAMES_VISIBLE_IPS`, and trust the internal proxy network with
`NAMES_TRUSTED_PROXY_IPS=172.16.0.0/12`. An exact IPv4 address can be listed as-is;
use `/128` for one IPv6 address or an appropriate delegated prefix such as `/64`
when the device portion rotates. Never put the Docker gateway (for example
`172.18.0.1`) in `NAMES_VISIBLE_IPS`, because it is shared by visitors using the
tunnel.

If Cloudflare Tunnel points only at the SvelteKit frontend instead, set
`INTERNAL_API_BASE=http://fastapi:8000`. The frontend proxies every `/api/...`
request to FastAPI and forwards Cloudflare's original visitor IP as a sanitized
internal header. Keeping browser requests on this single origin ensures the
name-access cookie is applied consistently on every page.

## Testing

Backend tests cover game payload validation, same-day rating recalculation, rating rebuilds, period rollovers, daily snapshot jobs, name privacy serialization/access rules, and the custom Elo implementation.

```bash
uv run --with pytest pytest backend/tests
```

Frontend quality checks:

```bash
cd front-end
npm run check
npm run lint
```

## Repository Layout

```text
backend/api/            FastAPI routers for players, games, stats, and leaderboard data
backend/db/             SQLModel models and database session setup
backend/ranking/        Custom Elo-style rating logic and rebuild helpers
backend/privacy.py      Optional player-name masking helpers
backend/jobs.py         Scheduled rating snapshots and period rollovers
front-end/              SvelteKit application
nginx/                  Reverse proxy configuration
docker/postgres/init/   PostgreSQL initialization scripts
babyfoot.sql            Seed data imported by PostgreSQL on first startup
docker-compose.yml      Local full-stack runtime
```

## GitHub Profile

Pin `Babyfoot` on your GitHub profile and place it above academic projects so visitors see it as a complete full-stack application first.
