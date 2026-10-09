import json
import tempfile
import unittest
from pathlib import Path

from ..agent.backend import Completion, ScriptedBackend
from ..agent.personas import create_agents
from ..games.wordle.bridge import WordleBridge
from ..games.wordle.dataset import WordlePuzzle
from ..games.wordle.engine import WordleGame
from ..play import play_wordle_game
from ..run_log import CallRecorder, RunLog


def decision_json(action: str, stop: bool) -> str:
    return json.dumps(
        {"action": action, "reason": "test reason", "stop": stop}
    )


def completion(action: str, stop: bool) -> Completion:
    return Completion(
        text=decision_json(action, stop),
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        model="test-model",
    )


class SequenceBackend:
    def __init__(self, items):
        self.items = list(items)

    def complete(self, messages):
        item = self.items.pop(0)

        if isinstance(item, Exception):
            raise item

        return item

    def stream(self, messages):
        yield self.complete(messages).text


class FailingBackend:
    def complete(self, messages):
        raise RuntimeError("provider unavailable")

    def stream(self, messages):
        raise RuntimeError("provider unavailable")


class DebateFlowTests(unittest.TestCase):
    def make_run(self, directory: str, **extra) -> RunLog:
        metadata = {"puzzle_id": "0", "target_answer": "CIGAR"}
        metadata.update(extra)

        return RunLog(
            metadata=metadata,
            path=Path(directory) / "run.json",
        )

    def make_game(self, max_attempts: int = 1) -> WordleGame:
        return WordleGame(
            WordlePuzzle("0", "CIGAR"),
            allowed_guesses={"CIGAR", "RAISE", "SLATE"},
            max_attempts=max_attempts,
        )

    def test_repair_success_records_usage(self):
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                Completion(
                    text=decision_json("Guess AUDIO", False),
                    prompt_tokens=9,
                    completion_tokens=6,
                    total_tokens=15,
                    model="test-model",
                ),
                completion("SLATE", False),
                completion("RAISE", False),
                completion("RAISE", True),
            ]
        )
        game = self.make_game()

        with tempfile.TemporaryDirectory() as directory:
            run = play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                agents=create_agents(backend=backend),
                run=self.make_run(directory),
                max_rounds=1,
                max_repairs=1,
                raise_errors=False,
            )

        self.assertEqual(run.data["status"], "completed")
        self.assertTrue(game.done)
        self.assertEqual(run.data["outcome"]["guesses_used"], 1)
        self.assertEqual(run.data["outcome"]["won"], False)
        self.assertEqual(
            run.data["counters"],
            {
                "agent_calls": 5,
                "rejected_responses": 1,
                "backend_errors": 0,
            },
        )

        usage = run.data["token_usage"]
        self.assertEqual(usage["calls"], 5)
        self.assertEqual(usage["calls_missing_usage"], 0)
        self.assertEqual(usage["prompt_tokens"], 49)
        self.assertEqual(usage["completion_tokens"], 26)
        self.assertEqual(usage["total_tokens"], 75)
        self.assertTrue(run.data["calls"][1]["rejected"])

    def test_repair_exhaustion_marks_failed(self):
        backend = ScriptedBackend(
            response=decision_json("Guess AUDIO", False)
        )
        game = self.make_game(max_attempts=6)

        with tempfile.TemporaryDirectory() as directory:
            run = play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                agents=create_agents(backend=backend),
                run=self.make_run(directory),
                max_rounds=1,
                max_repairs=1,
                raise_errors=False,
            )

            saved = json.loads(
                run.path.read_text(encoding="utf-8")
            )

        self.assertEqual(run.data["status"], "failed")
        self.assertEqual(run.data["error"]["type"], "ValueError")
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(run.data["outcome"]["guesses_used"], 0)
        self.assertIsNone(run.data["outcome"]["won"])
        self.assertFalse(run.data["outcome"]["game_finished"])

        counters = run.data["counters"]
        self.assertEqual(counters["agent_calls"], 2)
        self.assertEqual(counters["rejected_responses"], 2)
        self.assertEqual(counters["backend_errors"], 0)

        usage = run.data["token_usage"]
        self.assertIsNone(usage["total_tokens"])
        self.assertEqual(usage["calls_missing_usage"], 2)

    def test_backend_error_marks_failed_without_usage(self):
        game = self.make_game(max_attempts=6)

        with tempfile.TemporaryDirectory() as directory:
            run = play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                agents=create_agents(backend=FailingBackend()),
                run=self.make_run(directory),
                max_rounds=1,
                max_repairs=1,
                raise_errors=False,
            )

        self.assertEqual(run.data["status"], "failed")
        self.assertEqual(run.data["error"]["type"], "RuntimeError")
        self.assertEqual(run.data["counters"]["backend_errors"], 1)
        self.assertEqual(run.data["counters"]["agent_calls"], 1)
        self.assertEqual(run.data["outcome"]["guesses_used"], 0)
        self.assertIsNone(run.data["outcome"]["won"])
        self.assertIsNone(run.data["token_usage"]["total_tokens"])

    def test_raise_errors_propagates(self):
        game = self.make_game(max_attempts=6)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                play_wordle_game(
                    game=game,
                    bridge=WordleBridge(game),
                    agents=create_agents(backend=FailingBackend()),
                    run=self.make_run(directory),
                    max_rounds=1,
                    max_repairs=1,
                    raise_errors=True,
                )

            saved = json.loads(
                (Path(directory) / "run.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(saved["status"], "failed")

    def test_debate_continues_until_gm_stop(self):
        backend = SequenceBackend(
            [
                completion("CRANE", False),
                completion("SLATE", False),
                completion("CRANE", False),
                completion("CRANE", False),
                completion("RAISE", False),
                completion("CRANE", False),
                completion("CRANE", False),
                completion("SLATE", False),
                completion("CRANE", False),
                completion("CRANE", True),
            ]
        )
        game = WordleGame(
            WordlePuzzle("0", "CIGAR"),
            allowed_guesses={"CIGAR", "CRANE", "RAISE", "SLATE"},
            max_attempts=1,
        )

        with tempfile.TemporaryDirectory() as directory:
            run = play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                agents=create_agents(backend=backend),
                run=self.make_run(directory),
                max_rounds=3,
                max_repairs=1,
                raise_errors=False,
            )

        self.assertEqual(run.data["status"], "completed")

        turn = run.data["turns"][0]
        self.assertEqual(turn["debate_rounds"], 3)
        self.assertEqual(turn["gm_requested_stop"], True)
        self.assertEqual(turn["termination"], "gm_stop")
        self.assertEqual(run.data["counters"]["agent_calls"], 10)

    def test_usage_summary_stays_unknown_when_incomplete(self):
        recorder = CallRecorder()
        recorder.record(
            role="gm",
            attempt=0,
            rejected=False,
            error_type=None,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            elapsed_seconds=1.0,
        )
        recorder.record(
            role="negative",
            attempt=0,
            rejected=False,
            error_type=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            elapsed_seconds=1.0,
        )

        usage = recorder.token_usage()

        if usage is None:
            self.fail(
                "token_usage() must not be None when calls exist"
            )

        self.assertIsNone(usage["total_tokens"])
        self.assertEqual(usage["calls_with_usage"], 1)
        self.assertEqual(usage["calls_missing_usage"], 1)

    def test_observation_hides_answer(self):
        bridge = WordleBridge(self.make_game(max_attempts=6))
        self.assertNotIn("CIGAR", bridge.observe())


if __name__ == "__main__":
    unittest.main()
