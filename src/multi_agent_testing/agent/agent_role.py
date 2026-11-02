from enum import StrEnum


class AgentRole(StrEnum):
    GM = "gm"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    BOLD = "bold"
    CAUTIOUS = "cautious"
    CASUAL = "casual"
