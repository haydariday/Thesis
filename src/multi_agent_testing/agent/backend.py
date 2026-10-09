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
        temperature: float,
        api_key: str,
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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )

        choice = response.choices[0]
        content = choice.message.content

        if choice.finish_reason != "stop":
            raise RuntimeError(
                f"Model response did not finish normally: "
                f"{choice.finish_reason}"
            )

        if content is None or not content.strip():
            raise RuntimeError("The model returned an empty response.")

        usage = getattr(response, "usage", None)

        return Completion(
            text=content.strip(),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
            model=getattr(response, "model", None),
        )

    def stream(self, messages: Messages) -> Iterator[str]:
        finished = False
        chunks_seen = 0
        text_chunks = 0

        response_stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=True,
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
