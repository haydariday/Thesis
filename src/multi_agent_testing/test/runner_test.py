import contextlib
import io
import json
import sys
import tempfile
import unittest
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

    def start(self, *persona_args: str) -> str:
        return run_main(
            "start",
            "--experiment-dir", str(self.experiment),
            "--manifest", str(self.manifest),
            "--dataset", str(DATASET),
            "--guess-list", str(GUESSES),
            "--backend", "ollama",
            "--model", "scripted",
            "--base-url", "http://localhost:11434/v1",
            "--temperature", "0.2",
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


if __name__ == "__main__":
    unittest.main()
