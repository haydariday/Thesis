from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

Messages = list[ChatCompletionMessageParam]


class ModelBackend(Protocol):
    """The interface every backend must provide."""

    def complete(self, messages: Messages) -> str:
        ...

    def stream(self, messages: Messages) -> Iterator[str]:
        ...


@dataclass
class ScriptedBackend:
    """A test double, not an actual language model."""

    response: str = "Scripted response: the backend connection works."

    def complete(self, messages: Messages) -> str:
        return self.response

    def stream(self, messages: Messages) -> Iterator[str]:
        yield self.response


class ChatCompletionsBackend:
    """Generate responses through a local Ollama server."""

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

    def complete(self, messages: Messages) -> str:
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

        return content.strip()

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
