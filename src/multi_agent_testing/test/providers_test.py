import unittest
from datetime import UTC, datetime

from ..agent.providers import (
    default_api_key_env,
    endpoint_error,
    extra_body,
    peak_wait_seconds,
    settings_error,
)


def at(day: int, hour: int, minute: int = 0) -> datetime:
    # October 2026: the 13th is a Tuesday, the 17th a Saturday.
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


class EndpointTests(unittest.TestCase):
    def test_accepts_provider_hosts(self):
        self.assertIsNone(endpoint_error("zen", "https://opencode.ai/zen/v1/"))
        self.assertIsNone(endpoint_error("deepseek", "https://api.deepseek.com"))
        self.assertIsNone(endpoint_error("ollama", "http://localhost:11434/v1"))

    def test_rejects_lookalike_and_unsafe_urls(self):
        for backend, url in [
            ("zen", "https://opencode.ai.example.com/v1"),
            ("zen", "http://opencode.ai/zen/v1/"),
            ("deepseek", "https://opencode.ai/zen/v1/"),
            ("deepseek", "https://user:secret@api.deepseek.com"),
            ("deepseek", "https://api.deepseek.com?key=x"),
        ]:
            with self.subTest(url=url):
                self.assertIsNotNone(endpoint_error(backend, url))


class SettingsTests(unittest.TestCase):
    def test_deepseek_needs_an_explicit_mode(self):
        self.assertIn("--thinking", settings_error("deepseek", "chat", 0.2, None) or "")

    def test_deepseek_non_thinking_needs_temperature(self):
        self.assertIsNone(settings_error("deepseek", "chat", 0.2, "disabled"))
        self.assertIsNotNone(settings_error("deepseek", "chat", None, "disabled"))

    def test_deepseek_thinking_refuses_an_ignored_temperature(self):
        self.assertIsNone(settings_error("deepseek", "chat", None, "enabled"))
        self.assertIn("ignores temperature", settings_error("deepseek", "chat", 0.2, "enabled") or "")

    def test_deepseek_is_chat_only(self):
        self.assertIsNotNone(settings_error("deepseek", "responses", 0.2, "disabled"))

    def test_thinking_flag_is_deepseek_only(self):
        self.assertIsNotNone(settings_error("zen", "chat", 0.2, "disabled"))

    def test_zen_rules_are_unchanged(self):
        self.assertIsNone(settings_error("zen", "chat", 0.2, None))
        self.assertIsNotNone(settings_error("zen", "chat", None, None))
        self.assertIsNone(settings_error("zen", "responses", None, None))


class PeakHoursTests(unittest.TestCase):
    def test_inside_a_window_waits_until_it_ends(self):
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 1, 30)), 2.5 * 3600)
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 9, 59)), 60)

    def test_edges_and_off_peak(self):
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 4, 0)), 0)  # end is exclusive
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 0, 59)), 0)
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 12, 0)), 0)

    def test_margin_avoids_starting_a_game_just_before_a_window(self):
        # 00:58 plus a 3-minute margin reaches 01:00, so wait until 04:00.
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 0, 58), 180), 3 * 3600 + 2 * 60)
        self.assertEqual(peak_wait_seconds("deepseek", at(13, 0, 56), 180), 0)

    def test_weekends_and_other_backends_never_pause(self):
        self.assertEqual(peak_wait_seconds("deepseek", at(17, 2, 0)), 0)  # Saturday
        self.assertEqual(peak_wait_seconds("zen", at(13, 2, 0)), 0)
        self.assertEqual(peak_wait_seconds("ollama", at(13, 2, 0)), 0)


class ProviderDefaultsTests(unittest.TestCase):
    def test_key_names(self):
        self.assertEqual(default_api_key_env("zen"), "OPENCODE_API_KEY")
        self.assertEqual(default_api_key_env("deepseek"), "DEEPSEEK_API_KEY")
        self.assertIsNone(default_api_key_env("ollama"))

    def test_extra_body(self):
        self.assertIsNone(extra_body(None))
        self.assertEqual(extra_body("disabled"), {"thinking": {"type": "disabled"}})


if __name__ == "__main__":
    unittest.main()
