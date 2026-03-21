from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from sqlmodel import Session, select

from backend.consts import DEFAULT_COLOR
from backend.db.models import Game, Player, Team
from backend.db.session import engine
from backend.ranking import recalculate_all_ratings
from backend.settings import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30
REQUEST_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
}


@dataclass
class ScrapedMatch:
    game_timestamp: datetime
    team1_players: list[str]
    team2_players: list[str]
    result_team1: int
    result_team2: int


@dataclass
class ScrapedPlayer:
    player_name: str
    player_color: str
    active: bool


def _month_range(start_year: int, start_month: int) -> list[tuple[int, int]]:
    if start_month < 1 or start_month > 12:
        raise ValueError("POPULATE_START_MONTH must be between 1 and 12")

    now = datetime.now(tz=settings.tz)
    months: list[tuple[int, int]] = []
    for year in range(start_year, now.year + 1):
        first_month = start_month if year == start_year else 1
        last_month = now.month if year == now.year else 12
        for month in range(first_month, last_month + 1):
            months.append((year, month))
    return months


def _fetch_html(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def _fetch_players() -> list[ScrapedPlayer]:
    soup = BeautifulSoup(_fetch_html(settings.POPULATE_SOURCE_URL), "html.parser")
    rows = soup.find_all("td", class_="text-nowrap")

    players_by_name: dict[str, ScrapedPlayer] = {}
    for row in rows:
        name_el = row.find("span", class_="player-name")
        if name_el is None:
            continue
        player_name = name_el.get_text(strip=True)
        if not player_name:
            continue

        color_el = row.find("input", {"type": "color"})
        player_color = color_el.get("value") if color_el else None
        if not player_color:
            player_color = DEFAULT_COLOR

        active_checkbox = row.find("input", {"type": "checkbox", "name": "active"})
        active = bool(active_checkbox is not None and active_checkbox.has_attr("checked"))

        players_by_name[player_name] = ScrapedPlayer(
            player_name=player_name,
            player_color=player_color,
            active=active,
        )

    return list(players_by_name.values())


def _fetch_matches_for_month(year: int, month: int) -> list[ScrapedMatch]:
    url = f"{settings.POPULATE_SOURCE_URL.rstrip('/')}/?md={year}-{month:02d}"
    soup = BeautifulSoup(_fetch_html(url), "html.parser")

    matches_container = soup.find("div", id="matches")
    if matches_container is None:
        return []

    matches: list[ScrapedMatch] = []
    for item in matches_container.find_all("div", class_="accordion-item"):
        date_button = item.find("button", class_="accordion-button")
        if date_button is None:
            continue

        date_text = date_button.get_text(strip=True)
        try:
            day = datetime.strptime(date_text, "%d/%m/%Y").date()
        except ValueError:
            continue

        for row in reversed(item.find_all("div", class_="align-items-center")):
            time_tag = row.find_parent().find_parent().find("em")
            if time_tag is None:
                continue

            time_text = time_tag.get_text(strip=True)
            try:
                game_timestamp = datetime.strptime(f"{day} {time_text}", "%Y-%m-%d %H:%M").replace(tzinfo=settings.tz)
            except ValueError:
                continue

            players = row.find_all("div", class_="col-sm-3")
            results = row.find_all("div", class_="text-result")
            if len(players) < 2 or len(results) < 2:
                continue

            try:
                result_team1 = int(results[0].get_text(strip=True))
                result_team2 = int(results[1].get_text(strip=True))
            except ValueError:
                continue

            team1_players = [name.strip() for name in players[0].get_text("+").split("+") if name.strip()]
            team2_players = [name.strip() for name in players[1].get_text("+").split("+") if name.strip()]
            if not team1_players or not team2_players:
                continue

            matches.append(
                ScrapedMatch(
                    game_timestamp=game_timestamp,
                    team1_players=team1_players,
                    team2_players=team2_players,
                    result_team1=result_team1,
                    result_team2=result_team2,
                )
            )

    matches.sort(key=lambda match: match.game_timestamp)
    return matches


def _upsert_players(session: Session, scraped_players: list[ScrapedPlayer]) -> dict[str, Player]:
    existing_players = session.exec(select(Player)).all()
    players_by_name: dict[str, Player] = {player.player_name: player for player in existing_players}

    for scraped in scraped_players:
        player = players_by_name.get(scraped.player_name)
        if player is None:
            player = Player(
                player_name=scraped.player_name,
                player_color=scraped.player_color,
                active=scraped.active,
            )
            session.add(player)
            players_by_name[scraped.player_name] = player
        else:
            player.player_color = scraped.player_color
            player.active = scraped.active

    session.commit()
    return {player.player_name: player for player in session.exec(select(Player)).all()}


def populate_if_empty() -> bool:
    if not settings.AUTO_POPULATE_IF_EMPTY:
        logger.info("AUTO_POPULATE_IF_EMPTY disabled; skipping auto-population.")
        return False

    with Session(engine) as session:
        games_exist = session.exec(select(Game.id).limit(1)).first() is not None
        if games_exist:
            logger.info("Games already exist; skipping auto-population.")
            return False

    try:
        logger.info("Database is empty. Starting auto-population from %s", settings.POPULATE_SOURCE_URL)
        scraped_players = _fetch_players()
        if not scraped_players:
            logger.warning("No players found from source; skipping auto-population.")
            return False

        with Session(engine) as session:
            players_by_name = _upsert_players(session, scraped_players)
            inserted_games = 0
            skipped_games_missing_players = 0

            for year, month in _month_range(settings.POPULATE_START_YEAR, settings.POPULATE_START_MONTH):
                monthly_matches = _fetch_matches_for_month(year, month)
                if not monthly_matches:
                    continue

                for match in monthly_matches:
                    team1 = [players_by_name.get(name) for name in match.team1_players]
                    team2 = [players_by_name.get(name) for name in match.team2_players]
                    if any(player is None for player in team1 + team2):
                        skipped_games_missing_players += 1
                        continue

                    game = Game(
                        game_timestamp=match.game_timestamp,
                        result_team1=match.result_team1,
                        result_team2=match.result_team2,
                    )
                    session.add(game)
                    session.flush()

                    for player in team1:
                        session.add(Team(game_id=game.id, player_id=player.id, team_number=1))
                    for player in team2:
                        session.add(Team(game_id=game.id, player_id=player.id, team_number=2))

                    inserted_games += 1

                session.commit()

            recalculate_all_ratings(session)
            session.commit()
            logger.info(
                "Auto-population completed. Players=%s, games inserted=%s, games skipped (unknown players)=%s",
                len(players_by_name),
                inserted_games,
                skipped_games_missing_players,
            )
        return True
    except Exception:
        logger.exception("Auto-population failed.")
        return False
