import json
import tempfile
import unittest
from pathlib import Path

from ..agent.backend import Completion, ScriptedBackend
from ..agent.personas import create_lineup
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


class RecordingSequenceBackend(SequenceBackend):
    """SequenceBackend that also keeps each call's system prompt and payload."""

    def __init__(self, items):
        super().__init__(items)
        self.calls: list[tuple[str, dict]] = []

    def complete(self, messages):
        self.calls.append(
            (str(messages[0]["content"]), json.loads(str(messages[1]["content"])))
        )
        return super().complete(messages)


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
                lineup=create_lineup(backend, preset="pilot-01"),
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
                lineup=create_lineup(backend, preset="pilot-01"),
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
                lineup=create_lineup(FailingBackend(), preset="pilot-01"),
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
                    lineup=create_lineup(FailingBackend(), preset="pilot-01"),
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
                lineup=create_lineup(backend, preset="pilot-01"),
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

    def make_pilot_02_game(self) -> WordleGame:
        return WordleGame(
            WordlePuzzle("0", "CIGAR"),
            allowed_guesses={"CIGAR", "CRANE", "RAISE", "SLATE"},
            max_attempts=1,
        )

    def play(self, backend, preset: str, game: WordleGame, max_rounds: int) -> RunLog:
        with tempfile.TemporaryDirectory() as directory:
            return play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                lineup=create_lineup(backend, preset=preset),
                run=self.make_run(directory),
                max_rounds=max_rounds,
                max_repairs=1,
                raise_errors=False,
            )

    def test_pilot_01_action_rules_reject_and_repair(self):
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                completion("RAISE", False),  # Negative repeats: rejected
                completion("SLATE", False),
                completion("SLATE", False),  # Positive deviates: rejected
                completion("RAISE", False),
                completion("RAISE", True),
            ]
        )
        run = self.play(backend, "pilot-01", self.make_game(), max_rounds=1)

        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(
            run.data["counters"],
            {"agent_calls": 6, "rejected_responses": 2, "backend_errors": 0},
        )
        self.assertEqual(
            [call["role"] for call in run.data["calls"]],
            ["gm", "negative", "negative", "positive", "positive", "gm"],
        )

    def test_pilot_02_runs_three_advisors_in_order(self):
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                completion("SLATE", False),
                completion("CRANE", False),
                completion("RAISE", False),  # Casual agrees: allowed
                completion("CRANE", True),
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=1)

        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(
            run.data["counters"],
            {"agent_calls": 5, "rejected_responses": 0, "backend_errors": 0},
        )
        self.assertEqual(
            [call["role"] for call in run.data["calls"]],
            ["gm", "bold", "cautious", "casual", "gm"],
        )
        turn = run.data["turns"][0]
        self.assertEqual(turn["final_action"], "CRANE")
        self.assertEqual(turn["termination"], "gm_stop")
        self.assertEqual(
            [line.split(":")[0] for line in turn["transcript"]],
            [
                "GM proposes RAISE",
                "Bold Advisor suggests SLATE",
                "Cautious Advisor suggests CRANE",
                "Casual Advisor suggests RAISE",
                "GM reviews and selects CRANE",
            ],
        )

    def test_pilot_02_suggestions_reach_review_and_reset_each_round(self):
        backend = RecordingSequenceBackend(
            [
                completion("RAISE", False),
                completion("SLATE", False),
                completion("CRANE", False),
                completion("RAISE", False),
                completion("RAISE", False),  # review 1: continue
                completion("SLATE", False),
                completion("CRANE", False),
                completion("RAISE", False),
                completion("SLATE", True),  # review 2: stop
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=3)

        self.assertEqual(run.data["turns"][0]["debate_rounds"], 2)
        payloads = [payload for _, payload in backend.calls]
        review_1 = payloads[4]["suggestions"]
        self.assertEqual(list(review_1), ["bold", "cautious", "casual"])
        self.assertEqual(
            {key: value["action"] for key, value in review_1.items()},
            {"bold": "SLATE", "cautious": "CRANE", "casual": "RAISE"},
        )
        self.assertEqual(payloads[2]["suggestions"], {"bold": {"action": "SLATE", "reason": "test reason"}})
        self.assertEqual(payloads[5]["suggestions"], {})  # round 2, first advisor
        self.assertEqual(run.data["turns"][0]["final_action"], "SLATE")

    def test_pilot_02_reaches_round_cap_without_recursion_error(self):
        backend = ScriptedBackend(response=decision_json("RAISE", False))
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=3)

        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(run.data["counters"]["agent_calls"], 1 + 3 * 4)
        self.assertEqual(run.data["turns"][0]["termination"], "max_rounds")

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
