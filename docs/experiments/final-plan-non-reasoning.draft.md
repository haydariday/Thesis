# Draft: The non-reasoning configuration

Status: draft written on 3 November 2026, during F9, before any non-reasoning game. It is committed as a draft, to be merged into `final-plan.md` as Section 10 with the edits listed at the end. Supervisor sign-off pending.

## 10. The non-reasoning configuration

### 10.1 Purpose

The main study runs every condition with the model's reasoning mode. It is called the reasoning configuration (Sections 1 to 7). Its directories keep their names (`experiments/final-c1` to `final-c3`), since they were written during F9. The non-reasoning configuration runs the same three conditions with the reasoning mode off. Everything that makes up the framework stays fixed: the agents, the debate, the protocol, the prompts, the puzzles and the measures. Only the configuration of the model changes. This follows the design of Xiao and Yang [xiao2025], who kept their playtesting setup fixed and varied the prompting strategy.

The non-reasoning configuration adds no research question. It asks RQ1 to RQ3 a second time under another configuration, so the thesis can say whether their answers depend on the reasoning mode.

- **RQ1.** Is the system as consistent without the reasoning mode?
- **RQ2.** Does its agreement with human difficulty hold without the reasoning mode?
- **RQ3.** Do the personas still behave differently from each other?
- **Contrasts.** Do the debate effect (C3 − C2) and the persona effect (C1 − C3) point the same way in both configurations?

### 10.2 One factor

| | Reasoning configuration (Sections 1 to 7) | Non-reasoning configuration |
|---|---|---|
| Reasoning mode | on, effort low | **off** |
| Temperature | provider default (the reasoning mode ignores it) | **1.0**, the provider default |
| Prompts | zero-shot, no worked examples | the same |
| Everything else | Section 6.1 | the same |

Only the reasoning mode changes. Every prompt in both configurations is zero-shot, so the reasoning configuration reasons before answering and the non-reasoning configuration answers directly. Temperature 1.0 is the provider's default, so it is not a second factor. A lower temperature was rejected because it narrows sampling by itself, so a smaller within-puzzle SD would not show that the system is more consistent.

**Pilot evidence.** The pilot smoke-tested this setting as variant vC (thinking off, temperature 1.0, 12 guesses) on 16 games. It had a Spearman ρ of 0.13 and added noise that blurred the ranking (Section 6.2 of `pilot-02-plan.md`). The pilot's main configuration without the reasoning mode, vA, used temperature 0.2. In the pilot only the reasoning configuration showed personas that behaved differently from each other. The non-reasoning configuration may therefore be weaker on RQ2 and RQ3. That is a result to report, not a reason to change the setting.

### 10.3 Frozen non-reasoning configuration (tag `final-non-reasoning-frozen`)

Same as Section 6.1, with these changes:

| Item | Value |
|---|---|
| Sampling | thinking `disabled`, `--temperature 1.0`, `--max-tokens 8192`, JSON mode, no reasoning effort |
| Output | `experiments/final-nr-c1`, `experiments/final-nr-c2`, `experiments/final-nr-c3` |
| Puzzles | `experiments/manifests/final.csv`, the same 100 puzzles × 10 runs |
| Model snapshot | recorded at the smoke test |
| Code revision | the commit tagged `final-non-reasoning-frozen` |

The run rules of Section 6.2 apply: the three conditions in parallel with `--workers 4`, off-peak only, the fingerprint stop rule, one retry per failed game. The two configurations never pool.

Command sketch for C1 (C2 and C3 differ only in the persona flags and the output directory):

```bash
uv run python -u -m multi_agent_testing.experiment.runner start \
  --experiment-dir experiments/final-nr-c1 \
  --manifest experiments/manifests/final.csv \
  --dataset src/data/raw/worldepuzzles.json \
  --guess-list src/data/raw/allowed_guesses.txt \
  --backend deepseek --protocol chat --model deepseek-flash \
  --base-url https://api.deepseek.com \
  --thinking disabled --temperature 1.0 --max-tokens 8192 --json-mode \
  --max-guesses 6 --max-rounds 3 --max-repairs 2 --debate-protocol parallel \
  --request-timeout 300 --api-retries 1 \
  --repetitions 10 --max-attempts 2 --workers 4 \
  --persona-preset pilot-02
```

### 10.4 Analysis

**Within the non-reasoning configuration.** `analysis_final.py` runs on the three non-reasoning directories unchanged: the same measures, contrasts, Holm correction and persona check as Section 7.

**Reasoning against non-reasoning (fixed before any non-reasoning game).** For each condition, puzzle by puzzle on the same 100 puzzles:

- Within-puzzle SD, absolute error and signed error, reasoning − non-reasoning, with the two-sided Wilcoxon signed-rank test over puzzles. Holm correction over the three conditions, per measure.
- Spearman ρ, ICC(1,1) and tercile QWK of each configuration side by side, as values.
- The direction and significance of the debate effect, the persona effect and the persona check in each configuration.
- Cost per game (tokens, seconds, calls, repairs) in each configuration.

These tests are a second family next to the planned contrasts of Section 7. The comparison of the two configurations is reported as secondary: it describes how much the answers to RQ1 to RQ3 depend on the reasoning mode. It does not replace the main results, which stay those of the reasoning configuration.

The comparison needs a small script that reads both analysis outputs (`metrics.json` and `puzzle_summary.csv` of each configuration). It is written and tested before the non-reasoning configuration is frozen, so that the comparison is fixed before any non-reasoning game.

### 10.5 Cost and time

The pilot's configuration without the reasoning mode cost about $0.01 per persona-debate game (vA, about $5 for 528 games). Estimate before the smoke test: C1 about $10, C2 about $1, C3 about $10, about $21 in total, and well under a day of running with the three conditions in parallel. The smoke test replaces the estimate.

The budget in Section 6.3 rises to about $80 for both configurations, stopping for review above $95.

### 10.6 Phases

| Phase | Goal | Main tasks | Done when | Mode | Size |
|---|---|---|---|---|---|
| **F13** Non-reasoning plan | Fix the non-reasoning configuration before any of its games | Merge this section into the plan, update Sections 1, 3, 6.3 and 7.1. Write and test the comparison script. | The plan and the script are committed. | offline | S |
| **F14** Non-reasoning smoke | Measure before freezing | The smoke manifest × 2 games per condition under the non-reasoning configuration. | At least 15 of 16 games complete per condition, and the measured cost replaces Section 10.5. | live (tiny) | S |
| **F15** Non-reasoning freeze | Lock the non-reasoning configuration | Record the snapshot and code revision in Section 10.3. Tag `final-non-reasoning-frozen`. | The tag exists. | offline | S |
| **F16** Non-reasoning run | Collect 3,000 games | C1, C2 and C3 in parallel, 4 workers each. | 100 × 10 completed games per condition, or failures documented. | live | L |
| **F17** Non-reasoning analysis | Results and the comparison | `analysis_final.py` on the non-reasoning directories, then the comparison script. | Outputs exist in `experiments/final-nr-analysis` and `experiments/final-config-comparison`. | offline | S |

F11 (figures) and F12 (findings) then cover both configurations.

### 10.7 Edits to the rest of the plan when merged

- **Section 1:** a row "Configurations: reasoning (the main study) and non-reasoning (reasoning mode off, temperature 1.0), Section 10."
- **Section 3:** "The non-reasoning configuration adds no research question. It repeats RQ1 to RQ3 without the reasoning mode (Section 10)."
- **Section 6.3:** budget about $80 for both configurations, stop above $95.
- **Section 7.1:** replace "one model" in the last row with "one model in two configurations"; add that temperature is not varied and that the reasoning text is not logged, only its length within the completion tokens.
- **Section 8:** add F13 to F17.
- **Naming throughout:** "the reasoning configuration" for Sections 1 to 7 and "the non-reasoning configuration" for Section 10, in the plan and in the thesis. The pilot labels vA, vB and vC stay in `pilot-02-plan.md` only.
