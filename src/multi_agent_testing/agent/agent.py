from dataclasses import dataclass
from dis import Instruction
from .agent_role import AgentRole


@dataclass
class Agent:
    name: str
    role: AgentRole
    Instruction: Instruction
    tools_permissions: list[str]

    def build_message(self, context: str) -> list[dict]:
        