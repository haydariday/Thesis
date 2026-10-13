import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

from ..agent.backend import ScriptedBackend
from ..experiment import runner

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET = REPO_ROOT / "src" / "data" / "raw" / "worldepuzzles.json"
GUESSES = REPO_ROOT / "src" / "data" / "raw" / "allowed_guesses.txt"

# Puzzle 0 is CIGAR, so every scripted agent proposes the answer and the game
# ends after one debate turn.
WINNING_BACKEND = ScriptedBackend(
    response='{"action": "CIGAR", "reason": "scripted", "stop": false}'
)

OLLAMA = (
    "--backend", "ollama",
    "--base-url", "http://localhost:11434/v1",
    "--temperature", "0.2",
)
DEEPSEEK = (
    "--backend", "deepseek",
    "--base-url", "https://api.deepseek.com",
)


def run_main(*argv: str) -> str:
    output = io.StringIO()
    with (
        mock.patch.object(sys, "argv", ["runner", *argv]),
        mock.patch.object(runner, "build_backend", return_value=WINNING_BACKEND),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        runner.main()
    return output.getvalue()


@unittest.skipUnless(DATASET.exists() and GUESSES.exists(), "raw dataset not present")
class RunnerPersonaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "manifest.csv"
        self.manifest.write_text("puzzle_id\n0\n", encoding="utf-8")
        self.experiment = self.root / "exp"

    def tearDown(self):
        self.tmp.cleanup()

    def start(self, *persona_args: str, backend: tuple[str, ...] = OLLAMA) -> str:
        return run_main(
            "start",
            "--experiment-dir", str(self.experiment),
            "--manifest", str(self.manifest),
            "--dataset", str(DATASET),
            "--guess-list", str(GUESSES),
            "--model", "scripted",
            *backend,
            "--max-rounds", "1",
            "--repetitions", "1",
            *persona_args,
        )

    def config(self) -> dict:
        return json.loads((self.experiment / "experiment_config.json").read_text(encoding="utf-8"))

    def test_start_records_pilot_02_personas_in_config_and_run(self):
        self.start("--persona-preset", "pilot-02")

        personas = self.config()["settings"]["personas"]
        self.assertEqual(personas["preset"], "pilot-02")
        self.assertEqual(personas["gm"], "neutral_gm")
        self.assertEqual(personas["advisors"], ["bold", "cautious", "casual"])
        self.assertIn("rule out the most remaining letters", personas["specs"]["cautious"]["instruction"])

        run = json.loads((self.experiment / "runs" / "puzzle-0-rep1-attempt1.json").read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["metadata"]["personas"], personas)
        self.assertEqual(
            [call["role"] for call in run["calls"]],
            ["gm", "bold", "cautious", "casual", "gm"],
        )

    def test_start_with_explicit_advisors(self):
        self.start("--advisors", "cautious,bold", "--gm", "neutral_gm_v1")

        personas = self.config()["settings"]["personas"]
        self.assertIsNone(personas["preset"])
        self.assertEqual(personas["gm"], "neutral_gm_v1")
        self.assertEqual(personas["advisors"], ["cautious", "bold"])

    def test_resume_accepts_unchanged_personas(self):
        self.start("--persona-preset", "pilot-02-core")
        run_main("resume", "--experiment-dir", str(self.experiment))

    def test_resume_refuses_changed_persona_text(self):
        self.start("--persona-preset", "pilot-02")
        config = self.config()
        config["settings"]["personas"]["specs"]["bold"]["instruction"] += " Edited."
        (self.experiment / "experiment_config.json").write_text(json.dumps(config), encoding="utf-8")

        with self.assertRaises(SystemExit) as raised:
            run_main("resume", "--experiment-dir", str(self.experiment))
        self.assertIn("new configuration", str(raised.exception.code))

    def test_config_records_code_state(self):
        self.start("--persona-preset", "pilot-02")

        config = self.config()
        self.assertIn(config["code_dirty"], (True, False, None))
        self.assertEqual(len(config["source_sha256"]), 64)

    def test_resume_refuses_changed_source_code(self):
        self.start("--persona-preset", "pilot-02")

        with (
            mock.patch.object(runner, "source_hash", return_value="0" * 64),
            self.assertRaises(SystemExit) as raised,
        ):
            run_main("resume", "--experiment-dir", str(self.experiment))
        self.assertIn("source code changed", str(raised.exception.code))

    def test_start_rejects_bad_persona_flags(self):
        cases = [
            (),
            ("--persona-preset", "pilot-02", "--advisors", "bold"),
            ("--advisors", "bold,unknown"),
            ("--advisors", "bold,bold"),
        ]
        for flags in cases:
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as raised:
                self.start(*flags)
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(self.experiment.exists())


    def test_deepseek_records_thinking_mode_and_key_name(self):
        self.start(
            "--persona-preset", "pilot-02",
            backend=(
                *DEEPSEEK, "--thinking", "disabled", "--temperature", "0.2",
                "--max-tokens", "1024", "--json-mode",
            ),
        )

        settings = self.config()["settings"]
        self.assertEqual(settings["max_tokens"], 1024)
        self.assertTrue(settings["json_mode"])
        self.assertEqual(settings["thinking"], "disabled")
        self.assertEqual(settings["temperature"], 0.2)
        self.assertEqual(settings["api_key_env"], "DEEPSEEK_API_KEY")
        run = json.loads((self.experiment / "runs" / "puzzle-0-rep1-attempt1.json").read_text(encoding="utf-8"))
        self.assertEqual(run["metadata"]["thinking"], "disabled")

    def start_deepseek_at(self, now: datetime, *extra: str) -> list[float]:
        sleeps: list[float] = []
        with (
            mock.patch.object(runner, "_utcnow", return_value=now),
            mock.patch.object(runner, "_sleep", side_effect=sleeps.append),
        ):
            self.start(
                "--persona-preset", "pilot-02", *extra,
                backend=(*DEEPSEEK, "--thinking", "disabled", "--temperature", "0.2"),
            )
        return sleeps

    def test_deepseek_pauses_during_peak_hours(self):
        tuesday_2am = datetime(2026, 10, 13, 2, 0, tzinfo=UTC)

        self.assertEqual(self.start_deepseek_at(tuesday_2am), [2 * 3600])
        run = json.loads((self.experiment / "runs" / "puzzle-0-rep1-attempt1.json").read_text(encoding="utf-8"))
        self.assertEqual(run["status"], "completed")

    def test_allow_peak_does_not_pause(self):
        tuesday_2am = datetime(2026, 10, 13, 2, 0, tzinfo=UTC)

        self.assertEqual(self.start_deepseek_at(tuesday_2am, "--allow-peak"), [])

    def test_off_peak_does_not_pause(self):
        self.assertEqual(self.start_deepseek_at(datetime(2026, 10, 13, 12, 0, tzinfo=UTC)), [])

    def test_deepseek_rejects_settings_that_would_mislead(self):
        cases = [
            DEEPSEEK + ("--temperature", "0.2"),  # mode not chosen
            DEEPSEEK + ("--thinking", "enabled", "--temperature", "0.2"),  # ignored temperature
            ("--backend", "deepseek", "--base-url", "https://opencode.ai/zen/v1/", "--thinking", "disabled", "--temperature", "0.2"),
        ]
        for backend in cases:
            with self.subTest(backend=backend), self.assertRaises(SystemExit) as raised:
                self.start("--persona-preset", "pilot-02", backend=backend)
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(self.experiment.exists())


if __name__ == "__main__":
    unittest.main()
