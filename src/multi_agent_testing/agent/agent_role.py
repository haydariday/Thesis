from enum import StrEnum


class AgentRole(StrEnum):
    GM = "gm"
    NEGATIVE = "negative"
    POSITIVE = "positive"
    BOLD = "bold"
    CAUTIOUS = "cautious"
    CASUAL = "casual"
    NEUTRAL_1 = "neutral_1"
    NEUTRAL_2 = "neutral_2"
    NEUTRAL_3 = "neutral_3"
