import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from starlette.responses import Response
from starlette.requests import Request

from backend import privacy
from backend.schemas import (
    GameRead,
    PlayerRead,
    PlayerStats,
    RankRead,
    TeamRead,
    TeammateStat,
)


def make_request(
        *,
        headers: dict[str, str] | None = None,
        client_host: str = "203.0.113.10",
) -> Request:
    encoded_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": encoded_headers,
            "client": (client_host, 12345),
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )


class NamesPrivacyTests(unittest.TestCase):
    def test_names_visible_when_privacy_is_not_configured(self):
        request = make_request()

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", None),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", []),
        ):
            self.assertTrue(privacy.can_see_names(request))

    def test_password_header_allows_names(self):
        request = make_request(headers={privacy.NAMES_PASSWORD_HEADER: "secret"})

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", []),
        ):
            self.assertTrue(privacy.can_see_names(request))

    def test_signed_session_cookie_allows_names(self):
        login_request = make_request()
        response = Response()

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS", 60),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", []),
        ):
            privacy.issue_names_access_cookie(response, login_request)
            cookie_value = response.headers["set-cookie"].split(";", 1)[0]
            request = make_request(headers={"cookie": cookie_value})
            self.assertTrue(privacy.can_see_names(request))

    def test_invalid_session_cookie_does_not_allow_names(self):
        request = make_request(headers={"cookie": f"{privacy.NAMES_ACCESS_COOKIE}=v1.1.bad.bad"})

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_MAX_AGE_SECONDS", 60),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", []),
        ):
            self.assertFalse(privacy.can_see_names(request))

    def test_allowed_forwarded_ip_allows_names(self):
        request = make_request(
            headers={"x-forwarded-for": "198.51.100.23, 172.18.0.2"},
            client_host="172.18.0.2",
        )

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", ["198.51.100.0/24"]),
            patch.object(privacy.settings, "NAMES_TRUSTED_PROXY_IPS", ["172.18.0.0/16"]),
        ):
            self.assertTrue(privacy.can_see_names(request))

    def test_allowed_cloudflare_ipv6_from_trusted_proxy_allows_names(self):
        request = make_request(
            headers={"x-real-ip": "2a01:cb09:d040:78e1:243e:798:a827:ceff"},
            client_host="172.18.0.2",
        )

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", ["2a01:cb09:d040:78e1::/64"]),
            patch.object(privacy.settings, "NAMES_TRUSTED_PROXY_IPS", ["172.16.0.0/12"]),
        ):
            self.assertTrue(privacy.can_see_names(request))

    def test_untrusted_forwarded_ip_does_not_allow_names(self):
        request = make_request(
            headers={"x-forwarded-for": "198.51.100.23"},
            client_host="203.0.113.10",
        )

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", ["198.51.100.0/24"]),
            patch.object(privacy.settings, "NAMES_TRUSTED_PROXY_IPS", ["172.18.0.0/16"]),
        ):
            self.assertFalse(privacy.can_see_names(request))

    def test_denies_names_without_matching_password_or_ip(self):
        request = make_request(
            headers={privacy.NAMES_PASSWORD_HEADER: "wrong", "x-forwarded-for": "203.0.113.10"},
            client_host="203.0.113.10",
        )

        with (
            patch.object(privacy.settings, "NAMES_PRIVACY_PASSWORD", "secret"),
            patch.object(privacy.settings, "NAMES_PRIVACY_SESSION_SECRET", "session-secret"),
            patch.object(privacy.settings, "NAMES_VISIBLE_IPS", ["198.51.100.0/24"]),
            patch.object(privacy.settings, "NAMES_TRUSTED_PROXY_IPS", ["172.18.0.0/16"]),
        ):
            self.assertFalse(privacy.can_see_names(request))

    def test_masks_player_names_without_mutating_other_fields(self):
        player = PlayerRead(
            id=7,
            player_name="Alice",
            player_color="#f00",
            active=True,
            rating=RankRead(
                mu_overall=1000.0,
                sigma_overall=400.0,
                mu_monthly=1000.0,
                sigma_monthly=400.0,
                mu_yearly=1000.0,
                sigma_yearly=400.0,
                last_updated=datetime.now(timezone.utc),
            ),
        )

        masked = privacy.serialize_player(player, show_names=False)

        self.assertEqual(masked.player_name, "Joueur #7")
        self.assertEqual(masked.player_color, "#f00")
        self.assertEqual(player.player_name, "Alice")

    def test_masks_nested_game_and_teammate_names(self):
        player = PlayerRead(id=3, player_name="Bob", player_color="#00f", active=True)
        game = GameRead(
            id=1,
            game_timestamp=datetime.now(timezone.utc),
            result_team1=10,
            result_team2=8,
            teams=[TeamRead(player_id=3, team_number=1, player=player)],
        )
        stats = PlayerStats(
            games_played=5,
            wins=3,
            win_rate=0.6,
            average_team_score=8.0,
            average_opponent_score=7.0,
            best_teammate=TeammateStat(
                player_id=3,
                player_name="Bob",
                games_played=2,
                wins=2,
                win_rate=1.0,
            ),
            worst_teammate=None,
            current_win_streak=1,
            longest_win_streak=3,
        )

        masked_game = privacy.serialize_game(game, show_names=False)
        masked_stats = privacy.serialize_player_stats(stats, show_names=False)

        self.assertEqual(masked_game.teams[0].player.player_name, "Joueur #3")
        self.assertEqual(masked_stats.best_teammate.player_name, "Joueur #3")
        self.assertEqual(player.player_name, "Bob")


if __name__ == "__main__":
    unittest.main()
