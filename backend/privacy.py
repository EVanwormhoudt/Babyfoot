from __future__ import annotations

import base64
import hashlib
from hmac import compare_digest, new as hmac_new
from ipaddress import ip_address, ip_network
from secrets import token_urlsafe
from time import time
from typing import Iterable

from fastapi import Request
from starlette.responses import Response

from .schemas import GameRead, PlayerLeaderboard, PlayerRead, PlayerStats
from .settings import settings

NAMES_PASSWORD_HEADER = "x-names-password"
NAMES_ACCESS_COOKIE = "names_access"


def names_privacy_is_configured() -> bool:
    return bool(settings.NAMES_PRIVACY_PASSWORD or settings.NAMES_VISIBLE_IPS)


def _placeholder_name(player_id: int | None) -> str:
    if player_id is None:
        return "Joueur"
    return f"Joueur #{player_id}"


def _sign_session(message: str) -> str:
    secret = settings.NAMES_PRIVACY_SESSION_SECRET
    if not secret:
        return ""
    digest = hmac_new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _session_cookie_allows_names(request: Request) -> bool:
    token = request.cookies.get(NAMES_ACCESS_COOKIE)
    if not token or not settings.NAMES_PRIVACY_SESSION_SECRET:
        return False

    try:
        version, issued_at_raw, nonce, signature = token.split(".", 3)
        issued_at = int(issued_at_raw)
    except ValueError:
        return False

    if version != "v1":
        return False

    now = int(time())
    max_age = settings.NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS
    if issued_at > now + 60 or issued_at < now - max_age:
        return False

    message = f"{version}.{issued_at}.{nonce}"
    expected_signature = _sign_session(message)
    return bool(expected_signature) and compare_digest(signature, expected_signature)


def password_matches_configured_secret(provided_password: str) -> bool:
    configured_password = settings.NAMES_PRIVACY_PASSWORD
    if not configured_password:
        return False
    return compare_digest(provided_password, configured_password)


def issue_names_access_cookie(response: Response, request: Request) -> None:
    issued_at = int(time())
    message = f"v1.{issued_at}.{token_urlsafe(24)}"
    token = f"{message}.{_sign_session(message)}"
    secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip() == "https"
    )
    response.set_cookie(
        NAMES_ACCESS_COOKIE,
        token,
        max_age=settings.NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_names_access_cookie(response: Response) -> None:
    response.delete_cookie(NAMES_ACCESS_COOKIE, path="/", samesite="lax")


def _ip_in_networks(raw_ip: str | None, raw_networks: Iterable[str]) -> bool:
    if not raw_ip:
        return False
    try:
        candidate = ip_address(raw_ip)
    except ValueError:
        return False
    return any(candidate in ip_network(raw_network, strict=False) for raw_network in raw_networks)


def _request_ip_candidates(request: Request) -> Iterable[str]:
    if request.client and request.client.host:
        yield request.client.host

    if not _ip_in_networks(
        request.client.host if request.client else None,
        settings.NAMES_TRUSTED_PROXY_IPS,
    ):
        return

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        yield real_ip.strip()
        return

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            yield first_hop


def _ip_allows_names(request: Request) -> bool:
    if not settings.NAMES_VISIBLE_IPS:
        return False

    for raw_candidate in _request_ip_candidates(request):
        if _ip_in_networks(raw_candidate, settings.NAMES_VISIBLE_IPS):
            return True
    return False


def can_see_names(request: Request) -> bool:
    if not names_privacy_is_configured():
        return True
    header_password = request.headers.get(NAMES_PASSWORD_HEADER)
    return (
        _session_cookie_allows_names(request)
        or _ip_allows_names(request)
        or (header_password is not None and password_matches_configured_secret(header_password))
    )


def serialize_player(player: object, *, show_names: bool) -> PlayerRead:
    result = PlayerRead.model_validate(player)
    if show_names:
        return result
    return result.model_copy(update={"player_name": _placeholder_name(result.id)})


def serialize_players(players: Iterable[object], *, show_names: bool) -> list[PlayerRead]:
    return [serialize_player(player, show_names=show_names) for player in players]


def serialize_leaderboard_row(player: object, *, show_names: bool, **extra: object) -> PlayerLeaderboard:
    result = PlayerLeaderboard.model_validate({**PlayerRead.model_validate(player).model_dump(), **extra})
    if show_names:
        return result
    return result.model_copy(update={"player_name": _placeholder_name(result.id)})


def serialize_game(game: object, *, show_names: bool) -> GameRead:
    result = GameRead.model_validate(game)
    if show_names:
        return result

    masked_teams = []
    for team in result.teams:
        if team.player is None:
            masked_teams.append(team)
            continue
        masked_player = team.player.model_copy(
            update={"player_name": _placeholder_name(team.player.id)}
        )
        masked_teams.append(team.model_copy(update={"player": masked_player}))

    return result.model_copy(update={"teams": masked_teams})


def serialize_games(games: Iterable[object], *, show_names: bool) -> list[GameRead]:
    return [serialize_game(game, show_names=show_names) for game in games]


def serialize_player_stats(stats: PlayerStats, *, show_names: bool) -> PlayerStats:
    if show_names:
        return stats

    updates = {}
    if stats.best_teammate is not None:
        updates["best_teammate"] = stats.best_teammate.model_copy(
            update={"player_name": _placeholder_name(stats.best_teammate.player_id)}
        )
    if stats.worst_teammate is not None:
        updates["worst_teammate"] = stats.worst_teammate.model_copy(
            update={"player_name": _placeholder_name(stats.worst_teammate.player_id)}
        )
    return stats.model_copy(update=updates)
