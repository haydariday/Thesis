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
- `experiment.runner start|resume` — run a manifest of puzzles × repetitions into an experiment dir. Chunk long runs with `--max-seconds`, then `resume`. An existing dir must be resumed, not restarted.
- `experiment.analysis --experiment-dir …` — pilot-01 metrics (stdlib only).
- `experiment.manifest` — puzzle eligibility audit (`audit_record`, shared by later modules) and pilot-01 sampling.
- `experiment.manifest_pilot02` — pilot-02 deep/wide manifests, stratified by quartile (see README for the command).
- `experiment.human_data` — rebuilds `src/data/processed/wordle_human_clean.csv` and `quartiles.json`.
- `experiment.plots f1 …` — figures. They are built only from processed/analysis files, never raw logs.

Live runs need `OPENCODE_API_KEY` in the git-ignored `.env`. Never write it to source, configs or logs.

## Architecture

Flow of one game: `play.play_wordle_game` → `orchestra.debate.create_debate_graph` → LangGraph graph from `orchestra/flow/sequential.py` → `Agent`s calling a `ModelBackend`.

- **`agent/`** — `backend.py` defines the `ModelBackend` protocol plus `ScriptedBackend` (test double), chat-completions and responses backends for OpenAI-compatible endpoints (OpenCode Zen). `Completion` carries usage and the returned `model` (snapshot drift is tracked per call). `personas.py` builds the agents. It currently holds hard-coded GM/Negative/Positive (pilot-01). P4 turns it into a `PersonaSpec` registry with presets.
- **`orchestra/`** — `flow/sequential.py` owns only topology (`gm_propose → negative_challenge → positive_defend → gm_review → loop or finalize`). Node behavior and routing are injected by `debate.py`, which parses JSON `AgentDecision`s (`decision.py`), validates actions against the guess list, does up to `max_repairs` repair re-asks, and stops on GM `stop` or `max_rounds`. `debate_context.py` holds `DebateState`. P5 replaces the fixed advisor nodes and the `alternative` field with a per-advisor list and `suggestions`.
- **`games/wordle/`** — `engine.py` (rules and feedback), `dataset.py` (puzzle loading), `bridge.py` (renders public game state for prompts, validates actions). Agents only see public feedback. **Never put the answer word or human scores in any prompt.**
- **`run_log.py`** — `RunLog` checkpoints every turn to a run JSON. `CallRecorder` records per-call tokens, latency, rejections and model.
- **`experiment/`** — `runner.py` records config, code revision, source/data hashes and environment into `experiment_config.json`. It writes `runs/puzzle-<id>-rep<r>-attempt<a>.json`, `attempts.jsonl` and `run_summary.csv`, with retry attempts per unit. `manifest.py` holds the eligibility rules (`audit_record`) reused by `human_data.py`. `quartiles.py` does the rank-based D1–D4 split.

## Study conventions

- Loss is scored 7. Human 7-bin data: `p1..p6 = individual/100`, `p7 = (100 − sum)/100`.
- D1–D4 cut-points 3.98 / 4.24 / 4.53 are frozen in `src/data/processed/quartiles.json`. System scores map by value (`D1: s < 3.98`, …, `D4: s ≥ 4.53`).
- `experiments/<name>/` holds committed, canonical experiment outputs. `runs/` holds ad-hoc probes and smoke runs. `ready/` is git-ignored.
- Frozen configs and pooling rules are in the README. Any change to model, temperature, prompts/personas, `max_rounds`, `max_repairs`, data hashes or code revision makes a **new configuration**. Its games do not pool with earlier ones.
- `src/data/raw/worldepuzzles.json` keeps its filename typo on purpose (provenance).

## Writing

For thesis, proposal or conference prose (`docs/conference/`, `docs/proposal/`), use the `thesis-writing-style` skill (`.agents/skills/thesis-writing-style/`, symlinked into `.claude/skills/`).
