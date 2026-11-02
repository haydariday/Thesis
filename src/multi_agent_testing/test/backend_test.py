import unittest
from types import SimpleNamespace

from ..agent.backend import (
    ChatCompletionsBackend,
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



class ChatRequestTests(unittest.TestCase):
    """What the chat backend actually sends; no network calls."""

    def sent(self, finish_reason: str = "stop", content: str | None = '{"action": "CRANE"}', **kwargs) -> dict:
        backend = ChatCompletionsBackend(
            model="m", base_url="https://example.invalid/v1", api_key="k", **kwargs
        )
        captured: dict = {}

        def create(**request):
            captured.update(request)
            message = SimpleNamespace(content=content)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
                usage=SimpleNamespace(
                    prompt_tokens=30,
                    completion_tokens=19,
                    total_tokens=49,
                    prompt_cache_hit_tokens=24,
                ),
                model="m",
                system_fingerprint="fp-1",
            )

        backend.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))  # type: ignore[assignment]
        self.completion = backend.complete([{"role": "user", "content": "hi"}])
        return captured

    def test_fingerprint_and_cache_hits_are_kept(self):
        self.sent(temperature=0.2)

        self.assertEqual(self.completion.system_fingerprint, "fp-1")
        self.assertEqual(self.completion.cached_prompt_tokens, 24)

    def test_temperature_is_sent(self):
        request = self.sent(temperature=0.2)

        self.assertEqual(request["temperature"], 0.2)
        self.assertNotIn("extra_body", request)

    def test_thinking_switch_goes_in_extra_body(self):
        request = self.sent(temperature=0.2, extra_body={"thinking": {"type": "disabled"}})

        self.assertEqual(request["extra_body"], {"thinking": {"type": "disabled"}})

    def test_reply_cap_and_json_mode_are_sent(self):
        request = self.sent(temperature=0.2, max_tokens=1024, json_mode=True)

        self.assertEqual(request["max_tokens"], 1024)
        self.assertEqual(request["response_format"], {"type": "json_object"})

    def test_cut_off_and_empty_replies_return_with_usage(self):
        self.sent(temperature=0.2, finish_reason="length", content='{"action": "CR')
        self.assertEqual(self.completion.finish_reason, "length")
        self.assertEqual(self.completion.completion_tokens, 19)

        self.sent(temperature=0.2, content=None)
        self.assertEqual(self.completion.text, "")

    def test_other_abnormal_finishes_still_fail(self):
        with self.assertRaises(RuntimeError):
            self.sent(temperature=0.2, finish_reason="content_filter")

    def test_omitted_temperature_is_not_sent(self):
        request = self.sent(temperature=None, extra_body={"thinking": {"type": "enabled"}})

        self.assertNotIn("temperature", request)


if __name__ == "__main__":
    unittest.main()
