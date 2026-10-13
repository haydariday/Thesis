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

        # The GM's first proposal has no fallback, so the game still fails.
        self.assertEqual(run.data["status"], "failed")
        self.assertEqual(run.data["error"]["type"], "RepairExhausted")
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

    def test_cut_off_and_empty_replies_are_repaired(self):
        cut_off = Completion(
            text='{"action": "SLA',
            prompt_tokens=10,
            completion_tokens=1024,
            total_tokens=1034,
            finish_reason="length",
        )
        empty = Completion(text="", prompt_tokens=10, completion_tokens=0, total_tokens=10)
        backend = RecordingSequenceBackend(
            [
                completion("RAISE", False),
                cut_off,
                completion("SLATE", False),
                empty,
                completion("CRANE", False),
                completion("RAISE", False),
                completion("RAISE", True),
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=1)

        self.assertEqual(run.data["status"], "completed")
        rejected = [call for call in run.data["calls"] if call["rejected"]]
        self.assertEqual(
            [(call["role"], call["error_type"]) for call in rejected],
            [("bold", "TruncatedReply"), ("cautious", "EmptyReply")],
        )
        # The cut-off reply's tokens still count toward usage.
        self.assertEqual(rejected[0]["completion_tokens"], 1024)
        # Rejected text is kept for diagnosis; accepted calls store none.
        self.assertEqual(rejected[0]["rejected_text"], '{"action": "SLA')
        self.assertEqual(rejected[1]["rejected_text"], "")
        self.assertTrue(
            all(call["rejected_text"] is None for call in run.data["calls"] if not call["rejected"])
        )
        self.assertIn("cut off", backend.calls[2][1]["repair"]["validation_error"])

    def test_advisor_that_exhausts_repairs_abstains(self):
        backend = RecordingSequenceBackend(
            [
                completion("RAISE", False),
                completion("AUDIO", False),  # Bold: not in the vocabulary
                completion("T?A?E", False),  # Bold repair: still invalid
                completion("CRANE", False),
                completion("RAISE", False),
                completion("CRANE", True),
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=1)
        turn = run.data["turns"][0]

        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(turn["final_action"], "CRANE")
        self.assertEqual(turn["fallbacks"], ["abstained:bold"])
        bold = turn["advisor_suggestions"][0]
        self.assertEqual((bold["advisor"], bold["action"], bold["abstained"]), ("bold", None, True))
        self.assertIsNone(bold["agreed"])
        self.assertIsNone(turn["advisor_agreed"]["bold"])
        # The GM reviews without a Bold suggestion but sees the abstention.
        review = backend.calls[-1][1]
        self.assertEqual(list(review["suggestions"]), ["cautious", "casual"])
        self.assertIn("Bold Advisor abstains", review["transcript"][1])
        # The repair named the problem in plain terms.
        repair = backend.calls[2][1]["repair"]
        self.assertIn("AUDIO is not in the allowed vocabulary", repair["validation_error"])
        self.assertIn("Do not repeat the rejected action", repair["instruction"])

    def test_gm_review_that_exhausts_repairs_keeps_the_proposal(self):
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                completion("SLATE", False),
                completion("CRANE", False),
                completion("RAISE", False),
                completion("RAISE?", False),  # review: invalid
                completion("TOOLONG", False),  # review repair: invalid
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=1)
        turn = run.data["turns"][0]

        self.assertEqual(run.data["status"], "completed")
        self.assertEqual(turn["final_action"], "RAISE")
        self.assertEqual(turn["fallbacks"], ["gm_review_kept_proposal"])
        self.assertEqual(turn["termination"], "max_rounds")

    def test_repeated_guess_repair_lists_played_words(self):
        game = WordleGame(
            WordlePuzzle("0", "CIGAR"),
            allowed_guesses={"CIGAR", "CRANE", "RAISE", "SLATE"},
            max_attempts=2,
        )
        backend = RecordingSequenceBackend(
            [completion("SLATE", False)] * 4
            + [completion("SLATE", True)]
            + [completion("SLATE", False), completion("RAISE", False)]
            + [completion("RAISE", False)] * 3
            + [completion("RAISE", True)]
        )
        run = self.play(backend, "pilot-02", game, max_rounds=1)

        self.assertEqual(run.data["status"], "completed")
        message = backend.calls[6][1]["repair"]["validation_error"]
        self.assertEqual(
            message,
            "SLATE was already played. Already played: SLATE. "
            "Choose a word that has not been played.",
        )

    def test_missing_stop_means_continue_without_a_repair(self):
        no_stop = Completion(text='{"action": "SLATE", "reason": "test reason"}')
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                no_stop,
                no_stop,
                no_stop,
                Completion(text='{"action": "SLATE", "reason": "test reason"}'),  # review: no stop
                completion("SLATE", False),
                completion("SLATE", False),
                completion("SLATE", False),
                completion("SLATE", True),
            ]
        )
        run = self.play(backend, "pilot-02", self.make_pilot_02_game(), max_rounds=2)

        self.assertEqual(run.data["counters"]["rejected_responses"], 0)
        # The GM's missing stop at review 1 continued the debate to round 2.
        self.assertEqual(run.data["turns"][0]["debate_rounds"], 2)
        self.assertEqual(run.data["turns"][0]["termination"], "gm_stop")

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
        # Every agent gets the same reply-length limit.
        for system, _ in backend.calls:
            self.assertIn("at most two sentences and about 40 words", system)
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



class TurnStatisticsTests(unittest.TestCase):
    """Per-turn GM and persona statistics (pilot-02 plan, Section 2.3)."""

    # RAISE against CIGAR scores YYYBB, which leaves CIGAR and VIRAL.
    VOCABULARY = {"CIGAR", "CRANE", "RAISE", "SLATE", "VIRAL"}

    def play(self, backend, *, max_rounds: int = 1, max_attempts: int = 1) -> RunLog:
        game = WordleGame(
            WordlePuzzle("0", "CIGAR"),
            allowed_guesses=self.VOCABULARY,
            max_attempts=max_attempts,
        )
        with tempfile.TemporaryDirectory() as directory:
            return play_wordle_game(
                game=game,
                bridge=WordleBridge(game),
                lineup=create_lineup(backend, preset="pilot-02"),
                run=RunLog(metadata={}, path=Path(directory) / "run.json"),
                max_rounds=max_rounds,
                max_repairs=1,
                raise_errors=False,
            )

    @staticmethod
    def turn_backend(gm: str, bold: str, cautious: str, casual: str, review: str):
        return [
            completion(gm, False),
            completion(bold, False),
            completion(cautious, False),
            completion(casual, False),
            completion(review, True),
        ]

    def test_gm_retains_its_proposal(self):
        run = self.play(SequenceBackend(self.turn_backend("RAISE", "SLATE", "CRANE", "RAISE", "RAISE")))
        turn = run.data["turns"][0]

        self.assertEqual(turn["initial_proposal"], "RAISE")
        self.assertTrue(turn["gm_retained"])
        self.assertEqual(turn["adopted_from"], [])
        self.assertEqual(
            turn["advisor_agreed"],
            {"bold": False, "cautious": False, "casual": True},
        )
        self.assertEqual(
            [(s["round"], s["advisor"], s["action"], s["gm_proposal"]) for s in turn["advisor_suggestions"]],
            [(1, "bold", "SLATE", "RAISE"), (1, "cautious", "CRANE", "RAISE"), (1, "casual", "RAISE", "RAISE")],
        )
        # No feedback yet: every word could be the answer.
        self.assertEqual(turn["candidates_remaining"], 5)
        self.assertEqual(turn["is_candidate"], {"initial_proposal": True, "final_action": True})

    def test_gm_adopts_advisor_words(self):
        run = self.play(SequenceBackend(self.turn_backend("RAISE", "SLATE", "CRANE", "CRANE", "CRANE")))
        turn = run.data["turns"][0]

        self.assertEqual(turn["final_action"], "CRANE")
        self.assertFalse(turn["gm_retained"])
        self.assertEqual(turn["adopted_from"], ["cautious", "casual"])

    def test_gm_switches_to_a_word_no_advisor_offered(self):
        run = self.play(SequenceBackend(self.turn_backend("RAISE", "SLATE", "SLATE", "SLATE", "CRANE")))
        turn = run.data["turns"][0]

        self.assertFalse(turn["gm_retained"])
        self.assertEqual(turn["adopted_from"], [])

    def test_agreement_is_judged_against_each_round_proposal(self):
        backend = SequenceBackend(
            [
                completion("RAISE", False),
                completion("SLATE", False),
                completion("RAISE", False),  # cautious agrees in round 1
                completion("RAISE", False),  # casual agrees in round 1
                completion("SLATE", False),  # review 1: switch to SLATE, continue
                completion("SLATE", False),  # bold now agrees
                completion("RAISE", False),  # cautious now disagrees
                completion("SLATE", False),  # casual agrees again
                completion("SLATE", True),
            ]
        )
        turn = self.play(backend, max_rounds=2).data["turns"][0]

        self.assertEqual(turn["debate_rounds"], 2)
        self.assertEqual(
            [s["gm_proposal"] for s in turn["advisor_suggestions"]],
            ["RAISE"] * 3 + ["SLATE"] * 3,
        )
        self.assertEqual(
            [s["agreed"] for s in turn["advisor_suggestions"]],
            [False, True, True, True, False, True],
        )
        self.assertEqual(
            turn["advisor_agreed"],
            {"bold": False, "cautious": False, "casual": True},
        )
        self.assertEqual(turn["adopted_from"], ["bold", "casual"])

    def test_candidates_follow_public_feedback(self):
        backend = SequenceBackend(
            self.turn_backend("RAISE", "RAISE", "RAISE", "RAISE", "RAISE")
            + self.turn_backend("VIRAL", "CIGAR", "SLATE", "CRANE", "CIGAR")
        )
        run = self.play(backend, max_attempts=2)
        second = run.data["turns"][1]

        self.assertTrue(run.data["outcome"]["won"])
        self.assertEqual(run.data["turns"][0]["feedback"], "YYYBB")
        self.assertEqual(second["candidates_remaining"], 2)
        self.assertEqual(
            {s["advisor"]: s["is_candidate"] for s in second["advisor_suggestions"]},
            {"bold": True, "cautious": False, "casual": False},
        )
        self.assertEqual(second["is_candidate"], {"initial_proposal": True, "final_action": True})
        self.assertEqual(second["adopted_from"], ["bold"])

    def test_answer_never_appears_in_any_prompt(self):
        backend = RecordingSequenceBackend(
            self.turn_backend("RAISE", "SLATE", "CRANE", "VIRAL", "RAISE")
            + self.turn_backend("VIRAL", "SLATE", "CRANE", "VIRAL", "VIRAL")
        )
        run = self.play(backend, max_attempts=2)

        self.assertEqual(run.data["outcome"]["won"], False)
        self.assertEqual(len(backend.calls), 10)
        # The second turn's prompts carry real feedback, so the check is not vacuous.
        self.assertIn("YYYBB", json.dumps(backend.calls[5][1]))
        for system, payload in backend.calls:
            prompt = (system + json.dumps(payload)).upper()
            self.assertNotIn("CIGAR", prompt)


if __name__ == "__main__":
    unittest.main()
