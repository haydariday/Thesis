from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

Messages = list[ChatCompletionMessageParam]


@dataclass(frozen=True)
class Completion:
    """One model response with optional provider usage metadata."""

    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    model: str | None = None
    # Backend build ID; it changes when the provider swaps the model silently.
    system_fingerprint: str | None = None
    # Prompt tokens served from the provider's cache (billed at a lower rate).
    cached_prompt_tokens: int | None = None
    # "stop" for a complete reply; "length" when max_tokens cut it off.
    finish_reason: str | None = None


class UnusableReply(ValueError):
    """A reply that arrived but cannot be parsed; repaired like a bad decision."""


class TruncatedReply(UnusableReply):
    pass


class EmptyReply(UnusableReply):
    pass


def cached_prompt_tokens(usage: Any) -> int | None:
    """DeepSeek's cache-hit count, else the OpenAI-style cached token count."""

    hits = getattr(usage, "prompt_cache_hit_tokens", None)
    if hits is None:
        details = getattr(usage, "prompt_tokens_details", None)
        hits = getattr(details, "cached_tokens", None)
    return hits


class ModelBackend(Protocol):
    """The interface every backend must provide."""

    def complete(self, messages: Messages) -> Completion:
        ...

    def stream(self, messages: Messages) -> Iterator[str]:
        ...


@dataclass
class ScriptedBackend:
    """A test double, not an actual language model."""

    response: str = "Scripted response: the backend connection works."

    def complete(self, messages: Messages) -> Completion:
        return Completion(text=self.response)

    def stream(self, messages: Messages) -> Iterator[str]:
        yield self.response


class ChatCompletionsBackend:
    """Generate responses through an OpenAI-compatible endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str,
        temperature: float | None,
        api_key: str,
        request_timeout: float = 90.0,
        api_retries: int = 0,
        extra_body: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> None:
        if not api_key.strip():
            raise ValueError("An API key or local placeholder is required.")

        if not request_timeout > 0:
            raise ValueError("request_timeout must be positive.")

        if not 0 <= api_retries <= 2:
            raise ValueError("api_retries must be between 0 and 2.")

        if max_tokens is not None and max_tokens < 1:
            raise ValueError("max_tokens must be positive.")

        self.model = model
        self.temperature = temperature
        self.extra_body = extra_body
        self.max_tokens = max_tokens
        self.json_mode = json_mode

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=request_timeout,
            max_retries=api_retries,
        )

    def _sampling(self) -> dict[str, Any]:
        """Optional request fields; an omitted temperature is not sent."""

        options: dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.extra_body is not None:
            options["extra_body"] = self.extra_body
        if self.max_tokens is not None:
            options["max_tokens"] = self.max_tokens
        if self.json_mode:
            options["response_format"] = {"type": "json_object"}
        return options

    def complete(self, messages: Messages) -> Completion:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **self._sampling(),
        )

        choice = response.choices[0]
        content = choice.message.content

        # A cut-off or empty reply still returns its usage; Agent.decide
        # turns it into a repairable rejection.
        if choice.finish_reason not in ("stop", "length"):
            raise RuntimeError(
                f"Model response did not finish normally: "
                f"{choice.finish_reason}"
            )

        usage = getattr(response, "usage", None)

        return Completion(
            text=(content or "").strip(),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=getattr(response, "model", None),
            system_fingerprint=getattr(response, "system_fingerprint", None),
            cached_prompt_tokens=cached_prompt_tokens(usage),
            finish_reason=choice.finish_reason,
        )

    def stream(self, messages: Messages) -> Iterator[str]:
        finished = False
        chunks_seen = 0
        text_chunks = 0

        response_stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **self._sampling(),
        )

        with response_stream as chunks:
            for chunk in chunks:
                chunks_seen += 1

                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                content = choice.delta.content

                if content:
                    text_chunks += 1
                    yield content

                if choice.finish_reason is not None:
                    if choice.finish_reason != "stop":
                        raise RuntimeError(
                            "Model stream did not finish normally: "
                            f"{choice.finish_reason}"
                        )

                    finished = True

        if not finished:
            raise RuntimeError(
                "Model stream ended without a normal completion. "
                f"chunks_seen={chunks_seen}, "
                f"text_chunks={text_chunks}"
            )


def split_messages(
    messages: Messages,
) -> tuple[str | None, list[dict[str, str]]]:
    """Split chat-style messages into Responses instructions and input."""

    instructions: list[str] = []
    user_input: list[dict[str, str]] = []

    for message in messages:
        role = str(message.get("role", ""))
        content = message.get("content")

        if not isinstance(content, str):
            raise TypeError("Only text message content is supported.")

        if role == "system":
            instructions.append(content)
        else:
            user_input.append({"role": role, "content": content})

    joined = "\n\n".join(instructions) if instructions else None
    return joined, user_input


def completion_from_response(response: Any) -> Completion:
    """Map an SDK Responses result onto the local ``Completion`` type."""

    status = getattr(response, "status", None)

    if status is not None and status != "completed":
        raise RuntimeError(
            f"Model response did not finish normally: status={status}"
        )

    text = getattr(response, "output_text", None)

    if text is None or not text.strip():
        raise RuntimeError("The model returned an empty response.")

    usage = getattr(response, "usage", None)

    return Completion(
        text=text.strip(),
        prompt_tokens=getattr(usage, "input_tokens", None),
        completion_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
        model=getattr(response, "model", None),
    )


class ResponsesBackend:
    """Generate responses through an OpenAI-compatible Responses endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str,
        api_key: str,
        temperature: float | None = None,
        request_timeout: float = 90.0,
        api_retries: int = 0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("An API key or local placeholder is required.")

        if not request_timeout > 0:
            raise ValueError("request_timeout must be positive.")

        if not 0 <= api_retries <= 2:
            raise ValueError("api_retries must be between 0 and 2.")

        self.model = model
        self.temperature = temperature

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=request_timeout,
            max_retries=api_retries,
        )

    def complete(self, messages: Messages) -> Completion:
        instructions, user_input = split_messages(messages)

        extra: dict[str, Any] = {}

        if instructions is not None:
            extra["instructions"] = instructions

        if self.temperature is not None:
            extra["temperature"] = self.temperature

        response = self.client.responses.create(
            model=self.model,
            input=cast(Any, user_input),
            **extra,
        )

        return completion_from_response(response)

    def stream(self, messages: Messages) -> Iterator[str]:
        raise RuntimeError(
            "Streaming is not supported by the responses protocol backend."
        )
