import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from ..decision import AgentDecision
from .agent_role import AgentRole
from .backend import (
    Completion,
    EmptyReply,
    Messages,
    ModelBackend,
    TruncatedReply,
)
from .persona_spec import PersonaSpec


@dataclass
class Agent:
    name: str
    role: AgentRole
    instruction: str
    backend: ModelBackend
    persona: PersonaSpec
    last_completion: Completion | None = field(
        default=None,
        compare=False,
        repr=False,
    )

    def build_messages(self, context: str) -> Messages:
        """Prepare this agent's instruction and input."""

        return [
            {
                "role": "system",
                "content": self.instruction,
            },
            {
                "role": "user",
                "content": context,
            },
        ]

    def respond(self, context: str) -> str:
        """Ask the assigned backend to generate a response."""

        messages = self.build_messages(context)
        return self.backend.complete(messages).text

    def respond_stream(self, context: str) -> Iterator[str]:
        """Generate response text incrementally."""

        messages = self.build_messages(context)
        return self.backend.stream(messages)

    def decide(
        self,
        context: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> AgentDecision:
        """Request and validate a structured agent decision."""

        schema = json.dumps(AgentDecision.model_json_schema())

        instruction = (
            f"{self.instruction}\n\n"
            "Return exactly one JSON object matching this schema:\n"
            f"{schema}\n"
            "Do not include markdown fences or text outside the JSON. "
            "Keep reason short: at most two sentences and about 40 words. "
            "Advisors must set stop to false."
        )

        messages: Messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": context},
        ]

        self.last_completion = None

        if on_chunk is None:
            completion = self.backend.complete(messages)
            self.last_completion = completion
            raw_response = completion.text

            if completion.finish_reason == "length":
                raise TruncatedReply(
                    "The reply was cut off at the token limit. "
                    "Return only the JSON object with a shorter reason."
                )
            if not raw_response:
                raise EmptyReply(
                    "The reply was empty. Return the JSON object."
                )
        else:
            parts: list[str] = []

            for chunk in self.backend.stream(messages):
                on_chunk(chunk)
                parts.append(chunk)

            raw_response = "".join(parts)
            # Streaming responses do not report token usage yet.
            self.last_completion = Completion(text=raw_response)

        return AgentDecision.model_validate_json(raw_response)
