import unittest
from types import SimpleNamespace

from ..agent.backend import (
    Completion,
    completion_from_response,
    split_messages,
)


class SplitMessagesTests(unittest.TestCase):
    def test_system_and_user_messages(self):
        instructions, user_input = split_messages(
            [
                {"role": "system", "content": "You are a test."},
                {"role": "user", "content": '{"a": 1}'},
            ]
        )

        self.assertEqual(instructions, "You are a test.")
        self.assertEqual(
            user_input, [{"role": "user", "content": '{"a": 1}'}]
        )

    def test_multiple_system_messages_are_joined(self):
        instructions, user_input = split_messages(
            [
                {"role": "system", "content": "First."},
                {"role": "system", "content": "Second."},
                {"role": "user", "content": "Question."},
            ]
        )

        self.assertEqual(instructions, "First.\n\nSecond.")
        self.assertEqual(len(user_input), 1)

    def test_missing_system_message(self):
        instructions, user_input = split_messages(
            [{"role": "user", "content": "Question."}]
        )

        self.assertIsNone(instructions)
        self.assertEqual(len(user_input), 1)

    def test_non_text_content_is_rejected(self):
        with self.assertRaises(TypeError):
            split_messages(
                [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "hi"}],
                    }
                ]
            )


class CompletionFromResponseTests(unittest.TestCase):
    def make_response(self, **overrides):
        defaults = {
            "status": "completed",
            "output_text": "hello",
            "model": "gpt-6-luna",
            "usage": SimpleNamespace(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
        }
        defaults.update(overrides)

        return SimpleNamespace(**defaults)

    def test_maps_usage_and_model(self):
        completion = completion_from_response(self.make_response())

        self.assertIsInstance(completion, Completion)
        self.assertEqual(completion.text, "hello")
        self.assertEqual(completion.prompt_tokens, 10)
        self.assertEqual(completion.completion_tokens, 5)
        self.assertEqual(completion.total_tokens, 15)
        self.assertEqual(completion.model, "gpt-6-luna")

    def test_incomplete_status_is_rejected(self):
        with self.assertRaises(RuntimeError):
            completion_from_response(
                self.make_response(status="incomplete")
            )

    def test_empty_text_is_rejected(self):
        with self.assertRaises(RuntimeError):
            completion_from_response(
                self.make_response(output_text="   ")
            )

    def test_missing_usage_stays_unknown(self):
        completion = completion_from_response(
            self.make_response(usage=None)
        )

        self.assertIsNone(completion.prompt_tokens)
        self.assertIsNone(completion.completion_tokens)
        self.assertIsNone(completion.total_tokens)


if __name__ == "__main__":
    unittest.main()
