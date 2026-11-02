import json
import unittest
from pathlib import Path

from ..agent.agent_role import AgentRole
from ..agent.backend import Completion
from ..agent.persona_spec import ActionRule, PersonaSpec, Slot
from ..agent.personas import PERSONAS, PRESETS, create_lineup, lineup_from_config
from ..orchestra.debate import create_debate_graph
from ..orchestra.debate_context import new_debate_state

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
            lead = Slot.GM if preset.advisors else Slot.PLAYER
            self.assertEqual(PERSONAS[preset.gm].slot, lead, name)
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
        with self.assertRaises(ValueError):
            PersonaSpec(key="z", display_name="Z", slot=Slot.PLAYER, instruction="i")
        with self.assertRaises(ValueError):
            PersonaSpec(key="w", display_name="W", slot=Slot.PLAYER, instruction="i", task="t",
                        action_rule=ActionRule.MUST_EQUAL)


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
        self.assertEqual([a.persona.key for a in lineup.advisors], ["cautious", "bold"])
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
            {"advisors": ["bold"], "gm": "solo_player"},
            {"preset": "pilot-02", "gm": "solo_player"},
            {"preset": "solo", "gm": "neutral_gm"},
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                create_lineup(**kwargs)


class SoloLineupTest(unittest.TestCase):
    def test_solo_preset_has_one_player(self):
        lineup = create_lineup(preset="solo")
        self.assertTrue(lineup.solo)
        self.assertEqual(lineup.advisors, ())
        self.assertEqual(lineup.gm.persona, PERSONAS["solo_player"])
        self.assertEqual(lineup.gm.role, AgentRole.GM)
        self.assertFalse(create_lineup(preset="pilot-02").solo)

    def test_explicit_empty_advisors_need_a_player(self):
        self.assertTrue(create_lineup(advisors=[], gm="solo_player").solo)
        with self.assertRaises(ValueError):
            create_lineup(advisors=[], gm="neutral_gm")

    def test_player_prompt_names_no_debate(self):
        backend = TaskRecordingBackend()
        lineup = create_lineup(backend, preset="solo")
        create_debate_graph(lineup).invoke(new_debate_state("start", max_rounds=3))
        self.assertEqual(len(backend.tasks), 1)
        system, task = backend.tasks[0]
        self.assertEqual(task, PERSONAS["solo_player"].task)
        for word in ("advisor", "debate", "GM"):
            self.assertNotIn(word, system + task)

    def test_debate_prompts_keep_the_stop_rule(self):
        backend = TaskRecordingBackend()
        create_debate_graph(create_lineup(backend, preset="pilot-02")).invoke(
            new_debate_state("start", max_rounds=1)
        )
        for system, _ in backend.tasks:
            self.assertTrue(system.endswith(
                "Keep reason short: at most two sentences and about 40 words. "
                "Advisors must set stop to false."
            ))


class LineupConfigTest(unittest.TestCase):
    def test_round_trip_for_every_preset(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                block = create_lineup(preset=preset).config()
                self.assertEqual(lineup_from_config(block).config(), block)

    def test_round_trip_for_explicit_advisors(self):
        block = create_lineup(advisors=["casual", "bold"], gm="neutral_gm_v1").config()
        self.assertEqual(lineup_from_config(block).config(), block)

    def test_missing_block_means_pilot_01(self):
        self.assertEqual(lineup_from_config(None).config()["preset"], "pilot-01")

    def test_drifted_text_is_refused(self):
        block = create_lineup(preset="pilot-02").config()
        specs = dict(block["specs"])
        specs["casual"] = {**specs["casual"], "task": "changed"}
        with self.assertRaises(ValueError):
            lineup_from_config({**block, "specs": specs})

    def test_changed_preset_membership_is_refused(self):
        block = create_lineup(preset="pilot-02").config()
        with self.assertRaises(ValueError):
            lineup_from_config({**block, "advisors": ["bold", "cautious"]})


class Pilot01CompatibilityTest(unittest.TestCase):
    def test_lineup_keeps_roles_names_and_order(self):
        lineup = create_lineup(preset="pilot-01")
        self.assertEqual(
            [agent.role for agent in lineup.agents],
            [AgentRole.GM, AgentRole.NEGATIVE, AgentRole.POSITIVE],
        )
        self.assertEqual(
            [agent.name for agent in lineup.agents],
            ["Game Master", "Negative Advisor", "Positive Advisor"],
        )

    @unittest.skipUnless(PILOT_01_RUN.exists(), "pilot-01 run not present")
    def test_instructions_match_recorded_pilot_01_run(self):
        recorded = json.loads(PILOT_01_RUN.read_text(encoding="utf-8"))
        expected = recorded["metadata"]["agent_instructions"]
        self.assertEqual(create_lineup(preset="pilot-01").instructions(), expected)


class AdvisorTaskTest(unittest.TestCase):
    def test_each_advisor_receives_its_registry_task(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                backend = TaskRecordingBackend()
                lineup = create_lineup(backend, preset=preset)
                create_debate_graph(lineup).invoke(new_debate_state("start", max_rounds=1))
                sent = {
                    agent.persona.key: task
                    for system, task in backend.tasks
                    for agent in lineup.advisors
                    if system.startswith(agent.instruction)
                }
                expected = {
                    agent.persona.key: agent.persona.task
                    for agent in lineup.advisors
                }
                self.assertEqual(sent, expected)


if __name__ == "__main__":
    unittest.main()
