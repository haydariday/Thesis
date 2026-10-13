# Wordle Multi-Agent Playtesting

Persona-based multi-agent debate (Game Master + advisors, LangGraph) playing Wordle. System-validation study: RQ1 outcome consistency, RQ2 human difficulty alignment. Wordle only, no single-agent comparison in conference scope.

Global docs: `Wordle Multi-Agent Playtesting Research Context and Experiment Roadmap.md` (scope, RQ1/RQ2, milestones) + `docs/experiments/pilot-02-plan.md` (frozen pilot-02 design).

## Data provenance

- Raw puzzles: `https://engaging-data.com/pages/scripts/wordlebot/wordlepuzzles.js` → `src/data/raw/worldepuzzles.json` (typo preserved)
- Allowed guesses: `src/data/raw/allowed_guesses.txt`
- Never put answer words or human scores in agent prompts.
- Cleaned 7-bin human data (pilot-02 P1): `src/data/processed/wordle_human_clean.csv` + `.summary.json` (input hashes, counts). Bins `p1..p6 = individual/100`, `p7 = (100 - sum)/100` (fail). Same eligibility as pilot-01 (1,861 of 1,865 eligible; 26 duplicate answers flagged). Rebuild:

  ```bash
  uv run python -m multi_agent_testing.experiment.human_data \
    --dataset src/data/raw/worldepuzzles.json \
    --guess-list src/data/raw/allowed_guesses.txt \
    --output src/data/processed/wordle_human_clean.csv
  ```

  This also writes `src/data/processed/quartiles.json` (P2): D1–D4 by rank of human mean, sizes 465/465/465/466, cut-points 3.98/4.24/4.53, mapping rule for system scores. Figure F1: `experiments/pilot-02/figures/` (needs `uv sync --extra viz`).

## Quickstart

```bash
# smoke test, one game
uv run python -m multi_agent_testing.test.debate_test \
  --backend zen --protocol chat \
  --model glm-5.3-flash \
  --base-url 'https://opencode.ai/zen/v1/' \
  --temperature 0.2 --play --max-rounds 3 \
  --dataset src/data/raw/worldepuzzles.json \
  --puzzle-id 234 --guess-list src/data/raw/allowed_guesses.txt

# pilot-02 deep (example): 12 puzzles x 32 reps
uv run python -m multi_agent_testing.experiment.runner start \
  --experiment-dir experiments/pilot-02-deep \
  --manifest experiments/manifests/pilot-02-deep.csv \
  --dataset src/data/raw/worldepuzzles.json \
  --guess-list src/data/raw/allowed_guesses.txt \
  --backend zen --protocol chat --model glm-5.3-flash \
  --base-url 'https://opencode.ai/zen/v1/' \
  --temperature 0.2 --max-rounds 3 --max-repairs 1 \
  --request-timeout 300 --api-retries 1 \
  --repetitions 32 --max-attempts 2
```

Key in ignored `.env` as `OPENCODE_API_KEY`, never in source or logs.

## Frozen configs

- Pilot-01: `gpt-6-luna`, `responses`, temperature `null` (rejected by model), 20 puzzles x 3 reps. See `experiments/pilot-01/experiment_config.json`.
- Pilot-02: `glm-5.3-flash`, `chat`, temperature `0.2` (record before runs; low favors RQ1, high favors distribution spread — decide with supervisor), personas `bold/cautious/casual`, `max_rounds=3`, `max_repairs=1`, timeout 300, retries 1. Exp A deep 12 x 32, Exp B wide 48 x 3, disjoint, seeds `20261013`/`20261014`.

## Pilot → final reuse rules

1. Pooling within pilot-02 (Exp A + Exp B for mean alignment) is allowed only if model ID + returned snapshot, temperature, personas/prompts, `max_rounds`, `max_repairs`, dataset/vocab hashes, and code revision are identical. Report pooled runs separately from primary.
2. Final evaluation runs on fresh puzzles. Pilot puzzles stay out of the final N. Pilot-01's 20 are already excluded from pilot-02 sampling.
3. If pilot results change prompts, temperature, model, or any setting, that creates a new configuration — do not count old games toward final N; show them only as sensitivity analysis.
4. Pre-register the pooling rule and equivalence tolerance before the final run. No post-hoc promotion of pooled results to primary.
5. Zen snapshots drift silently: check per-call returned `model`. If snapshot differs between pilot and final, treat as different model, no pooling.
