import json
import unittest
from pathlib import Path

from ..agent.agent_role import AgentRole
from ..agent.backend import Completion
from ..agent.persona_spec import ActionRule, PersonaSpec, Slot
from ..agent.personas import PERSONAS, PRESETS, create_agents, create_lineup
from ..orchestra.debate import create_debate_graph

REPO_ROOT = Path(__file__).resolve().parents[3]
PILOT_01_RUN = REPO_ROOT / "experiments" / "pilot-01" / "runs" / "puzzle-234-rep1-attempt1.json"


class TaskRecordingBackend:
    """Answers RAISE (the Negative says SLATE) and records each call's task."""

    def __init__(self):
        self.tasks: list[tuple[str, str]] = []

    def complete(self, messages):
        system = str(messages[0]["content"])
        payload = json.loads(str(messages[1]["content"]))
        self.tasks.append((system, payload["task"]))
        action = "SLATE" if system.startswith("You are the Negative advisor") else "RAISE"
        return Completion(text=json.dumps({"action": action, "reason": "r", "stop": False}))

    def stream(self, messages):
        yield self.complete(messages).text


class RegistryTest(unittest.TestCase):
    def test_presets_reference_known_personas_in_the_right_slot(self):
        for name, preset in PRESETS.items():
            self.assertEqual(PERSONAS[preset.gm].slot, Slot.GM, name)
            for key in preset.advisors:
                self.assertEqual(PERSONAS[key].slot, Slot.ADVISOR, name)

    def test_action_rules(self):
        self.assertEqual(PERSONAS["negative"].action_rule, ActionRule.MUST_DIFFER)
        self.assertEqual(PERSONAS["positive"].action_rule, ActionRule.MUST_EQUAL)
        for key in ("bold", "cautious", "casual"):
            self.assertEqual(PERSONAS[key].action_rule, ActionRule.ANY)

    def test_every_advisor_key_is_a_role(self):
        for spec in PERSONAS.values():
            if spec.slot == Slot.ADVISOR:
                AgentRole(spec.key)

    def test_spec_validation(self):
        with self.assertRaises(ValueError):
            PersonaSpec(key="x", display_name="X", slot=Slot.ADVISOR, instruction="i")
        with self.assertRaises(ValueError):
            PersonaSpec(key="y", display_name="Y", slot=Slot.GM, instruction="i", task="t")


class LineupTest(unittest.TestCase):
    def test_pilot_02_order_and_roles(self):
        lineup = create_lineup(preset="pilot-02")
        self.assertEqual(lineup.preset, "pilot-02")
        self.assertEqual(lineup.gm.role, AgentRole.GM)
        self.assertEqual(lineup.gm.persona, PERSONAS["neutral_gm"])
        self.assertEqual(
            [agent.role for agent in lineup.advisors],
            [AgentRole.BOLD, AgentRole.CAUTIOUS, AgentRole.CASUAL],
        )

    def test_explicit_advisors_default_to_neutral_gm(self):
        lineup = create_lineup(advisors=["cautious", "bold"])
        self.assertEqual(lineup.gm.persona, PERSONAS["neutral_gm"])
        self.assertEqual([a.persona.key for a in lineup.advisors if a.persona], ["cautious", "bold"])
        self.assertIsNone(lineup.preset)

    def test_gm_override(self):
        lineup = create_lineup(preset="pilot-02-core", gm="neutral_gm_v1")
        self.assertEqual(lineup.gm.persona, PERSONAS["neutral_gm_v1"])

    def test_invalid_requests(self):
        cases = [
            {},
            {"preset": "pilot-02", "advisors": ["bold"]},
            {"preset": "missing"},
            {"advisors": []},
            {"advisors": ["bold", "bold"]},
            {"advisors": ["unknown"]},
            {"advisors": ["neutral_gm"]},
            {"advisors": ["bold"], "gm": "bold"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                create_lineup(**kwargs)


class Pilot01CompatibilityTest(unittest.TestCase):
    def test_create_agents_keeps_roles_names_and_order(self):
        agents = create_agents()
        self.assertEqual(list(agents), [AgentRole.GM, AgentRole.NEGATIVE, AgentRole.POSITIVE])
        self.assertEqual(
            [agent.name for agent in agents.values()],
            ["Game Master", "Negative Advisor", "Positive Advisor"],
        )

    @unittest.skipUnless(PILOT_01_RUN.exists(), "pilot-01 run not present")
    def test_instructions_match_recorded_pilot_01_run(self):
        recorded = json.loads(PILOT_01_RUN.read_text(encoding="utf-8"))
        expected = recorded["metadata"]["agent_instructions"]
        actual = {role.value: agent.instruction for role, agent in create_agents().items()}
        self.assertEqual(actual, expected)

    def test_advisor_tasks_match_what_the_debate_sends(self):
        backend = TaskRecordingBackend()
        agents = create_agents(backend=backend)
        graph = create_debate_graph(agents)
        graph.invoke({
            "context": "start",
            "proposal": "",
            "alternative": "",
            "transcript": [],
            "final_action": "",
            "round": 0,
            "max_rounds": 1,
            "stop": False,
        })
        sent = {
            role: task
            for system, task in backend.tasks
            for role in (AgentRole.NEGATIVE, AgentRole.POSITIVE)
            if system.startswith(agents[role].instruction)
        }
        self.assertEqual(sent[AgentRole.NEGATIVE], PERSONAS["negative"].task)
        self.assertEqual(sent[AgentRole.POSITIVE], PERSONAS["positive"].task)


if __name__ == "__main__":
    unittest.main()
