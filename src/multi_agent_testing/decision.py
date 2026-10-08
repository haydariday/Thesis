from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentDecision(BaseModel):
    """Shared debate response, independent of a specific game."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
    )

    action: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=2000)
    stop: bool

    @field_validator("action", "reason")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot contain only whitespace.")

        return value
