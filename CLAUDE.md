# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Thesis research code: a persona-based multi-agent debate (Game Master + advisors, built on LangGraph) plays Wordle as an automated playtester. It is a system-validation study. RQ1 is outcome consistency across repeated runs. RQ2 is alignment with human difficulty. Scope is Wordle only, with no single-agent condition.

Key docs (read before changing experiment behavior):
- `docs/experiments/pilot-02-plan.md` — frozen pilot-02 design and the P0–P15 phase table. Each phase is one commit on branch `pilot-2`, prefixed `P<n>:`.
- `docs/Wordle Multi-Agent Playtesting Research Context and Experiment Roadmap.md` — scope, RQs, milestones.
- `README.md` — data provenance, frozen configs, pilot→final reuse rules.

## Commands

Python 3.12, managed with `uv`. Package lives in `src/multi_agent_testing`.

```bash
uv sync                      # core deps
uv sync --extra viz          # adds matplotlib for experiment/plots.py

# All offline tests (stdlib unittest; test/ has no __init__.py, so `discover` finds nothing)
uv run python -m unittest $(ls src/multi_agent_testing/test/*_test.py | grep -v debate_test.py \
  | sed 's|src/||; s|\.py$||; s|/|.|g')

# One module / one test
uv run python -m unittest multi_agent_testing.test.quartiles_test
uv run python -m unittest multi_agent_testing.test.debate_flow_test.<Class>.<method>
```

`test/debate_test.py` is **not** a unit test. It is a CLI that plays a live game (see the README smoke-test command) and spends API tokens.

Type checking: pyright, `standard` mode, configured in `pyrightconfig.json` (`extraPaths: ["src"]`). There is no linter or formatter configured.

Other entry points (all `uv run python -m multi_agent_testing.…`):
- `experiment.runner start|resume` — run a manifest of puzzles × repetitions into an experiment dir. `start` requires `--persona-preset` or `--advisors` (flags from `agent/persona_args.py`, shared with `debate_test`). Chunk long runs with `--max-seconds`, then `resume`. An existing dir must be resumed, not restarted. `resume` rebuilds personas from `settings.personas` and refuses if the registry text changed (`personas.lineup_from_config`).
- `experiment.analysis --experiment-dir …` — pilot-01 metrics (stdlib only).
- `experiment.manifest` — puzzle eligibility audit (`audit_record`, shared by later modules) and pilot-01 sampling.
- `experiment.manifest_pilot02` — pilot-02 deep/wide manifests, stratified by quartile (see README for the command).
- `experiment.human_data` — rebuilds `src/data/processed/wordle_human_clean.csv` and `quartiles.json`.
- `experiment.plots f1 …` — figures. They are built only from processed/analysis files, never raw logs.

Live runs need `DEEPSEEK_API_KEY` (pilot-02, `--backend deepseek`) or `OPENCODE_API_KEY` (`--backend zen`) in the git-ignored `.env`. Never write keys to source, configs or logs. Provider hosts, key names and DeepSeek's `--thinking` rule live in `agent/providers.py`.

## Architecture

Flow of one game: `play.play_wordle_game(lineup=…)` → `orchestra.debate.create_debate_graph(lineup)` → LangGraph graph from `orchestra/flow/sequential.py` → `Agent`s calling a `ModelBackend`. A `Lineup` (GM + ordered advisors) comes from `personas.create_lineup(backend, preset=… | advisors=[…])`.

- **`agent/`** — `backend.py` defines the `ModelBackend` protocol plus `ScriptedBackend` (test double), chat-completions and responses backends for OpenAI-compatible endpoints (OpenCode Zen). `Completion` carries usage and the returned `model` (snapshot drift is tracked per call). `personas.py` is the persona registry (`PERSONAS`, `PRESETS`, `create_lineup`). `PersonaSpec` (`persona_spec.py`) holds each persona's instruction, advisor task and `action_rule`. Pilot-01 instruction text must stay byte-identical (`personas_test` checks it against a recorded pilot-01 run).
- **`orchestra/`** — `flow/sequential.py` owns only topology: `gm_propose → advisor_<key> … → gm_review → next round or finalize`, one node per advisor in line-up order. Node behavior and routing are injected by `debate.py`, which parses JSON `AgentDecision`s (`decision.py`), validates actions against the guess list and each advisor's `action_rule`, does up to `max_repairs` repair re-asks, and stops on GM `stop` or `max_rounds`. `DebateState.suggestions` (`debate_context.py`) holds the current round's `{advisor_key: {action, reason}}` and is cleared after each GM review. `suggestion_log` keeps every round for statistics and is never sent to agents. Logged call `role` is `gm` or the advisor key.
- **`games/wordle/`** — `engine.py` (rules and feedback), `dataset.py` (puzzle loading), `bridge.py` (renders public game state for prompts, validates actions), `candidates.py` (`known_letters` keyboard-style summary shown to agents, plus candidate filtering for statistics; both use public feedback only). Agents only see public feedback. **Never put the answer word or human scores in any prompt.**
- **`play.py`** — `turn_statistics` adds the per-turn GM/persona fields (`gm_retained`, `adopted_from`, `advisor_agreed`, `is_candidate`, `candidates_remaining`; plan Section 2.3). Candidates come from `games/wordle/candidates.py`, which uses public feedback only.
- **`run_log.py`** — `RunLog` checkpoints every turn to a run JSON. `CallRecorder` records per-call tokens (including cached prompt tokens), latency, rejections, model, `system_fingerprint` and the raw text of rejected replies. In `backend.py`, a reply cut off at `max_tokens` or empty raises `TruncatedReply`/`EmptyReply` (both `ValueError`), so it gets the repair re-ask instead of failing the game. `AgentDecision.stop` defaults to `false`.
- **`experiment/`** — `runner.py` records config, code revision, source/data hashes and environment into `experiment_config.json`. It writes `runs/puzzle-<id>-rep<r>-attempt<a>.json`, `attempts.jsonl` and `run_summary.csv`, with retry attempts per unit. `manifest.py` holds the eligibility rules (`audit_record`) reused by `human_data.py`. `quartiles.py` does the rank-based D1–D4 split.

## Study conventions

- Loss is scored 7. Human 7-bin data: `p1..p6 = individual/100`, `p7 = (100 − sum)/100`.
- D1–D4 cut-points 3.98 / 4.24 / 4.53 are frozen in `src/data/processed/quartiles.json`. System scores map by value (`D1: s < 3.98`, …, `D4: s ≥ 4.53`).
- `experiments/<name>/` holds committed, canonical experiment outputs. `runs/` holds ad-hoc probes and smoke runs. `ready/` is git-ignored.
- Frozen configs and pooling rules are in the README. Any change to model, temperature, prompts/personas, `max_rounds`, `max_repairs`, data hashes or code revision makes a **new configuration**. Its games do not pool with earlier ones.
- `src/data/raw/worldepuzzles.json` keeps its filename typo on purpose (provenance).

## Writing

For thesis, proposal or conference prose (`docs/conference/`, `docs/proposal/`), use the `thesis-writing-style` skill (`.agents/skills/thesis-writing-style/`, symlinked into `.claude/skills/`).
