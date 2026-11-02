# Final Study Plan: Persona Debate Against a Single Agent and a Debate Without Personas

Drafted: 2 November 2026. Status: F0 decisions recorded on 2 November 2026; supervisor sign-off of the items in Section 9 is still pending. The study runs on branch `final-experimentation`. Each phase below is one commit on that branch, prefixed `F<n>:`.

The pilot validated the persona-based debate on its own. The final study adds two reference conditions, so that it can say what the debate adds over one agent and what the personas add over a debate without them. All three conditions use the reasoning configuration of the pilot (configuration vB, Section 6.3 of `pilot-02-plan.md`), since it was the only one in which the personas behaved differently from each other.

## 1. Decisions recorded

| Topic | Decision |
|---|---|
| Model settings | Configuration vB for every condition: `deepseek-flash` with thinking `enabled`, reasoning effort `low`, `max_tokens=4096`, JSON mode, no temperature. |
| Guess limit | 6, hidden from the agents as in the pilot. A loss scores 7, the same scale as the human data. |
| Conditions | C1 persona debate, C2 single agent, C3 debate without personas (Section 2). |
| Size | 100 fresh puzzles (33, 33 and 34 per human tercile) × 10 runs × 3 conditions = 3,000 games (Section 5). |
| Pairing | Every condition plays the same 100 puzzles with the same 10 repetitions, so every comparison is paired by puzzle. |
| Difficulty categories | Terciles (cut-points 4.07 and 4.42 over the 1,861 eligible puzzles), as decided in the progress report on 2026-10-23. The puzzles are drawn by tercile (changed from quartiles on 2 November 2026, before any final game). Quartiles stay as a sensitivity check. Adopted at F0, frozen at F1 in `terciles.json`. |
| Reporting | Values with p-values, without resampling. Spearman ρ and Pearson r carry their t-test p-values as in the pilot, paired condition contrasts use the Wilcoxon signed-rank test over puzzles, and the persona checks use rank tests over games (Section 7). Decided on 2 November 2026, replacing the bootstrap intervals of the draft. |
| Budget | About $55 including retries and smoke tests. Stop and review above $70 (Section 6.3). Adopted at F0. |
| Debate protocol | `parallel`: the advisors of a round answer independently (Section 2.0). Changed from the pilot's `sequential` protocol after the F7 smoke tests. |
| Pooling | None. The new code makes this a new configuration, so no pilot game counts toward the final study (README reuse rule 3). |

## 2. Conditions

| | C1 Persona debate | C2 Single agent | C3 Debate without personas |
|---|---|---|---|
| Agents | GM + Bold, Cautious, Casual | one player agent | GM + three neutral advisors |
| Per turn | propose, 3 advisors, review, up to 3 rounds | one decision | as C1 |
| Personas | the pilot-02 registry text, unchanged | none | none |
| Isolates | the full system | the reference point | the effect of the personas |

The contrasts are planned in advance:

- **Debate effect:** C3 against C2. Same model and prompts style, with and without the debate.
- **Persona effect:** C1 against C3. Same debate, with and without playstyle personas.

C1 against C2 is reported as the overall difference but is not a separate test.

### 2.0 Debate protocol

The final study uses the **parallel** protocol (decided on 2 November 2026, the default of the runner flag `--debate-protocol`, recorded in each config):

- **`parallel`** (final study, default): each advisor reads the GM's proposal and the transcript up to the start of the round, but not the other advisors' advice of that round. The advisors of a round therefore answer independently, as if in parallel, while the GM review still sees every suggestion. Later rounds see the earlier rounds in full. This follows debates in which agents see each other's answers only from the previous round [Du et al.]. The order and conformity papers that motivate it came from search summaries and must be verified before citing (`suggestion.md`).
- **`sequential`** (the pilot protocol): each advisor also reads the suggestions of the earlier advisors in the same round. It stays selectable with `--debate-protocol sequential`, so the pilot can be reproduced. Configs written before the flag existed resume as `sequential`.

Why the change: the F7 smoke runs under `sequential` showed that later advisors mostly repeat the first dissent (herding, Section 6.4), and that the fixed order ties each persona to one position. Under `parallel` neither can happen within a round. The cost is that the final system differs from the one the pilot validated: the persona text, GM and game knowledge are unchanged, but the advisors no longer hear each other within a round. C2 has no advisors, so the protocol does not affect it. The advisors are still called in the fixed order, which no longer matters within a round.

### 2.1 C2 single agent

C2 plays the game, as the single agents of Xiao and Yang do. It does not rate difficulty, since a rating could not be compared with guess counts. The agent receives the same game knowledge, bridge output and reply format as the debate agents. Each turn it returns one decision, which the bridge validates and plays. Invalid replies get the same repair re-asks as in C1.

Instruction draft (`solo_player`, frozen at F8):

> You are a player in a Wordle playtesting system. Choose the next guess based on the available game state and explain your choice briefly. Do not invent game feedback.

This text reuses the neutral GM wording without the debate references, so the only difference from C3's GM is the missing debate.

Implemented at F3 as preset `solo` (persona `solo_player`, slot `player`). Task draft: "Choose the next guess and explain why. Set stop to false." The player's request holds only the game state and the task, with no proposal, suggestions or transcript. Its system prompt also leaves out the sentence on advisors and the schema description ("Shared debate response …"), which every debate agent still receives unchanged. Its calls are logged with role `gm`, and each turn ends with termination `single_decision`.

### 2.2 C3 neutral advisors

C3 keeps the GM and the three advisor slots of C1. The three advisors share one instruction with no playstyle, under three keys (`neutral_1`, `neutral_2`, `neutral_3`) so the debate and the statistics still tell them apart.

Instruction draft (`neutral_advisor`, frozen at F8):

> You are an advisor in a Wordle playtesting system. Critique the GM's proposal and suggest a better guess if one exists. If you see no clear improvement, return the proposal unchanged.

Task draft: "Critique the current GM proposal. If you see a better guess, suggest it and explain why. Otherwise return the proposal unchanged. Set stop to false."

Revised after the first F7 smoke test. The first draft asked for "the guess you think is best", and 37 of C3's 38 truncated replies were empty: the model spent all 4096 tokens searching for an optimum. The revision asks for an improvement, with the same structure as the persona prompts and without a playstyle. Its smoke test is `runs/final-smoke-c3b`.

The pilot-02 persona text stays byte-identical, since `resume` refuses a changed registry and C1 must match the persona design reported in Chapter 3.

Implemented at F4 as preset `neutral`: `neutral_gm` with `neutral_1`, `neutral_2` and `neutral_3` (display names "Advisor 1" to "Advisor 3"), which share the instruction and task above and have no action rule. A test checks the `pilot-02` preset against the persona block recorded in `experiments/pilot-02-vb-wide/experiment_config.json`.

## 3. Research questions

The three research questions keep their wording. C2 and C3 add no research question of their own. They serve as baselines inside the existing questions, mainly RQ2, so the study stays a validation of the persona debate. Adopted at F0. The roadmap and README now include C2 and C3 in the final-study scope. The thesis still uses RQ3 for the expert evaluation, so the RQ3 numbering stays open for the supervisor (Section 9).

- **RQ1.** How consistent are the playtest outcomes across repeated runs on the same puzzles?
- **RQ2.** To what extent do the difficulty estimates agree with human difficulty, measured by average guess scores and difficulty categories?
- **RQ3.** How do the playstyle personas behave during the debate, and how strongly do their suggestions shape the final guesses?

How the baselines enter each question:

| RQ | Role of C2 and C3 |
|---|---|
| RQ1 | Reference values in the same table: within-puzzle SD and ICC for each condition. |
| RQ2 | Main use. ρ, bias and MAE for each condition, plus the two paired contrasts (Section 7) to show whether C1 agrees with humans better than either baseline. |
| RQ3 | C3 is the baseline of the persona check. The personas count as working only if Cautious pulls away from Bold in C1 more than the second neutral advisor pulls away from the first in C3, at the same speaking positions (Section 7). |

## 4. Puzzles

- **Pool:** the 1,861 eligible puzzles of `wordle_human_clean.csv`, minus the pilot-01 puzzles, both pilot-02 manifests and duplicate answers.
- **Draw:** 33 puzzles from T1, 33 from T2 and 34 from T3, 100 in total, with seed `20261103`. The hardest tercile gets the hundredth puzzle, since its range is the widest. Stratifying by the category scheme that RQ2 scores gives every category a third of the puzzles. The first draw (25 per quartile) gave 35, 31 and 34 per tercile, since the tercile cuts fall inside D2 and D3, and it was replaced before any final game.
- **Smoke manifest:** 8 puzzles (2 per quartile, seed `20261104`) taken from the pilot-02 wide manifest, so the smoke games never touch a final puzzle.
- **Drawn at F2:** pool 1,729 after excluding the 80 pilot puzzles. The final set holds 25 D1, 22 D2, 28 D3 and 25 D4 puzzles. Human means range from 3.40 to 4.05 in T1, 4.08 to 4.40 in T2 and 4.43 to 6.09 in T3 (`experiments/manifests/final.summary.json`).
- Agents never see the answer word, the guess limit or any human result.

## 5. Sample-size justification

The sizes come from a simulation calibrated on the pilot (`docs/experiments/final-power-sim.py`). It draws puzzles from the real human means and generates whole-number guess counts with configuration vB's noise and bias. At the pilot's own sizes it reproduces the observed values (48 × 3 gives ρ about 0.26 to 0.33 and ICC(1,1) about 0.21 to 0.36, against the observed 0.28 and 0.25). The pilot places the true correlation at about 0.4 to 0.6.

Power of Spearman ρ against zero (α = 0.05, 2,000 simulated studies per cell, two values of the between-puzzle spread):

| Design | Games per condition | True ρ = 0.4 | True ρ = 0.5 | True ρ = 0.6 |
|---|---|---|---|---|
| 60 × 10 | 600 | 74–80% | 92–96% | 98–100% |
| 60 × 32 | 1,920 | 81–84% | 96–97% | 100% |
| 100 × 5 | 500 | 83–92% | 96–99% | 100% |
| **100 × 10** | **1,000** | **92–95%** | **99–100%** | **100%** |

- **Puzzles drive the power.** RQ2 is a correlation across puzzles, so 100 × 5 beats 60 × 32 with fewer games.
- **Ten runs are enough per puzzle.** By the Spearman–Brown relation, the reliability of a puzzle mean is about 0.77 to 0.89 at 10 runs and only 0.91 to 0.96 at 32. Adding subjects improves a reliability study more than adding repeats once each subject has a few [Walter, Eliasziw and Donner 1998].
- **RQ1 needs no deep set.** At 100 × 10 the simulated 95% range of ICC(1,1) is about ±0.07 to 0.08, and 100 puzzles exceed the 30 subjects recommended for an ICC study [Koo and Li 2016].
- **Condition contrasts rest on paired measures.** The simulated MAE is precise to about ±0.07 to 0.08, so paired MAE and bias differences of about 0.15 guesses are detectable. A difference between two correlations would need several hundred puzzles, so ρ is tested against zero per condition and its differences are reported descriptively.
- **Limits.** Exact category matches stay low in every design, because the system's scores tie: about 0.35 to 0.43 with quartiles and 0.46 to 0.53 with terciles (chance is 0.25 and 0.33). The 7-bin distribution comparison is pooled by category, since 10 runs give each bin share a margin of about ±36 points [Thompson 1987].

- **Tercile stratification (rerun on 2 November 2026, mode `terciles`).** Drawing 33/33/34 per tercile instead of 25 per quartile leaves the power, ρ, ICC(1,1) and MAE unchanged at 100 × 10 (for example power 91–95% at a true ρ of 0.4, and ICC(1,1) 0.21 or 0.36 depending on the between-puzzle spread). Only the exact category rate rises, because there are three categories instead of four.

The references in this section were cited from memory and must be checked before they enter the thesis. The list, with the order and conformity papers behind Section 2.0, is in `suggestion.md`.

## 6. Configuration and run

### 6.1 Frozen configuration (F8, tag `final-frozen`)

| Item | Value |
|---|---|
| Backend | DeepSeek API, chat protocol, `deepseek-flash`. Record the returned `model` and `system_fingerprint` of every call. |
| Sampling | thinking `enabled`, `--reasoning-effort low`, `--max-tokens 4096`, JSON mode, no temperature |
| Game | `--max-guesses 6`, hidden from the agents |
| Debate (C1, C3) | `--max-rounds 3`, `--max-repairs 2`, `--debate-protocol parallel` |
| C2 | one decision per turn, `--max-repairs 2` |
| Requests | `--request-timeout 300 --api-retries 1 --max-attempts 2` |
| Personas | C1 `--persona-preset pilot-02`, C2 `--persona-preset solo`, C3 `--persona-preset neutral` |
| Runs | `--repetitions 10`, `--workers 4` per condition, the three conditions at the same time (12 games at once, as in F7 without rate limits) |
| Output | `experiments/final-c1`, `experiments/final-c2`, `experiments/final-c3` |
| Model snapshot | `system_fingerprint` `bc19ba97cbe016479903222bb1578db6` on all F7 calls; returned `model` `deepseek-flash` |
| Code revision | the commit tagged `final-frozen`; every condition must record it with `code_dirty: false` |
| Persona text | `agent/personas.py` at the tag: `neutral_gm`, `bold`, `cautious`, `casual` (pilot-02 text, checked against the vB config), `solo_player`, `neutral_1..3` (revised wording, Section 2.2) |
| Manifest | `experiments/manifests/final.csv` (100 puzzles, 33/33/34 per tercile), sha256 `7cbc9c0d725d2002cf7a980a0f85ba9faa03770c8c728bc8c1a512c97e8b68c0` |
| Data | dataset `ed235aa7…41a27`, guess list `9df5dad1…a121e`, clean CSV `3f15e93b…3b3a8`, `terciles.json` `5296a727…61c7fd`, `quartiles.json` `d91925d7…0a6d` (sha256) |
| Environment | Python 3.12.14, langgraph 1.2.13, openai 3.26.0, pydantic 2.13.5 |

Frozen on 2 November 2026 (F8). After the tag, nothing in Sections 1, 2 or 6 changes. A change would make a new configuration whose games do not pool with these.

### 6.2 Run rules

1. Run all three conditions from the tag with a clean tree. Commit nothing until the last condition has finished, so the three share one `code_revision`.
2. **Run the conditions in parallel.** Start C1, C2 and C3 at the same time, each in its own terminal with `--workers 4`, rather than one after another. A model update during the run then affects all three at the same moment instead of one condition. (Changed on 2 November 2026 from alternating 2-hour chunks, before any final game. The runner's results do not depend on the worker count.) A condition that stops is continued with `resume --workers 4`.
3. **Fingerprint stop rule.** Check the `system_fingerprint` after the first few hours and then at least daily. If it changes, pause all conditions and decide before continuing. Games on two fingerprints are reported separately.
4. Off-peak only, as the runner enforces by default (no `--allow-peak`).
5. A failed game is retried once. Games still missing after two attempts are documented, and the analysis repeats RQ2 with them scored as losses (the existing `missing_as_loss` check).

Command sketch for C1 (C3 and C2 differ only in the persona flags and the output directory):

```bash
uv run python -m multi_agent_testing.experiment.runner start \
  --experiment-dir experiments/final-c1 \
  --manifest experiments/manifests/final.csv \
  --dataset src/data/raw/worldepuzzles.json \
  --guess-list src/data/raw/allowed_guesses.txt \
  --backend deepseek --protocol chat --model deepseek-flash \
  --base-url 'https://api.deepseek.com' \
  --thinking enabled --reasoning-effort low --max-tokens 4096 --json-mode \
  --max-guesses 6 --max-rounds 3 --max-repairs 2 --debate-protocol parallel \
  --request-timeout 300 --api-retries 1 \
  --repetitions 10 --max-attempts 2 --workers 4 \
  --persona-preset pilot-02
```

### 6.3 Cost and time

Prices are DeepSeek's off-peak rates per 1M tokens ($0.003 cache hit, $0.15 cache miss, $0.60 output; checked 2026-11-02, thinking billed the same). C1 is calculated from the token counts logged in the 532 vB attempts (41k prompt tokens with 44% from cache, 30k completion tokens and 43 calls per game). The vB pilot itself comes to $11.31 by this calculation, which should be checked against the DeepSeek usage page.

| Condition | Games | Off-peak cost | Basis | Time with 4 workers |
|---|---|---|---|---|
| C1 persona debate | 1,000 | about $20 | measured at F7 ($0.0196 per game) | about 14 h |
| C2 single agent | 1,000 | about $2 | measured at F7 ($0.0016 per game) | about 1.5 h |
| C3 debate without personas | 1,000 | about $22 | measured at F7 with the revised prompt ($0.0218 per game) | about 16 h |
| **Total** | **3,000** | **about $44** | | **about 16 h** with the three conditions in parallel (C1 and C3 side by side, plus peak-hour pauses) |

The draft estimates were $21, $4 and $21 (C1 from the 532 vB attempts, C2 and C3 assumed). F7 replaced them with the smoke measurements below.

Budget about $55 including retries and smoke tests. Stop and review if the spend passes $70.

### 6.4 Smoke test results (F7, 2 November 2026)

Smoke manifest × 2 games per condition, settings of Section 6.1 with `--workers 4` and the **sequential** debate protocol (before the switch to parallel), code revision `4585702`, clean tree. The three conditions ran at the same time. Outputs are in `runs/final-smoke-c1`, `-c2` and `-c3`.

| | C1 | C2 | C3 |
|---|---|---|---|
| Completed games | 16 / 16 | 16 / 16 | 16 / 16 |
| Wins | 16 | 16 | 16 |
| Mean score | 3.81 | 3.62 | 3.88 |
| Calls per game | 38.6 | 3.7 | 32.9 |
| Prompt / completion tokens per game | 36k (41% cached) / 27k | 1.9k (59% cached) / 2.4k | 29k (49% cached) / 31k |
| Seconds per game | 208 | 19 | 225 |
| Cost per game | $0.0196 | $0.0016 | $0.0209 |
| Truncated replies (`max_tokens`) | 5 of 618 calls (all Cautious) | 1 of 59 | **38 of 526** (neutral_1 18, neutral_2 10, neutral_3 10) |
| Advisor abstentions | 0 | – | 2 (neutral_1) |

- One `system_fingerprint` (`bc19ba97…`) on all 1,203 calls. No rate-limit or backend errors with 12 games running at once.
- C3's advisors argue without playstyles: no persona names, and their reasons use generic Wordle strategy ("information", "candidate").
- Debate rounds in C1 match the vB pilot. C3's GM stops after one round more often (26 of 58 turns against 7 of 61 in C1).
- **Herding in C3.** When a later neutral advisor disagrees with the GM, it nearly always repeats the earlier advisor's alternative (neutral_2 17 of 20, neutral_3 21 of 23). Cautious almost never does (1 of 99), Casual sometimes (9 of 43). The fixed speaking order therefore shapes C3 more than C1 (see Section 9).
- `analysis_final` ran on the three smoke directories without errors. With 8 puzzles its values are not results.

**C3 rerun with the revised neutral prompt** (`runs/final-smoke-c3b`, code revision `00cd914`, Section 2.2):

| | C3 first draft | C3 revised |
|---|---|---|
| Completed / wins | 16 / 16 | 16 / 16 |
| Mean score | 3.88 | 3.75 |
| Truncated replies | 38 of 526 (7.2%) | 15 of 600 (2.5%) |
| Advisor abstentions | 2 | 0 |
| Agreement with the GM (neutral_1 / 2 / 3) | 82% / 81% / 79% | 87% / 83% / 82% |
| Later dissent repeats an earlier one | 38 of 43 | 36 of 46 |
| Turns ending at the round cap | 4 of 62 | 15 of 60 |
| Calls / cost per game | 32.9 / $0.0209 | 37.5 / $0.0218 |

The revision cut truncations to about a third and removed the abstentions, so `max_tokens` stays at 4096 for all conditions. Herding is unchanged. The GM now runs more rounds, so the cost per game stays about the same. The revised prompt is the C3 configuration for F8.

Open before F8 (Section 9): whether to add a herding statistic.

## 7. Analysis

A new `experiment/analysis_final.py` reads the three experiment directories, reusing the helpers of `analysis.py` and `analysis_pilot02.py`. It refuses to run if the three configs differ in anything other than the persona setup and the output directory.

**Per condition (RQ1 to RQ3).**

| RQ | Measures |
|---|---|
| RQ1 | Within-puzzle SD, ICC(1,1) and ICC(1,10), each ICC with its F-distribution 95% interval |
| RQ2 | Spearman ρ with p-value (primary), Pearson r with p-value, bias and MAE with the constant-guess baseline, rank-based terciles (exact and adjacent, quadratic-weighted κ) |
| RQ3 (C1, C3) | GM retention, adoption and agreement per advisor, non-candidate share per advisor after turn 1, herding per advisor, and the persona check below |

**Baseline contrasts (inside RQ1 to RQ3).** For the debate effect (C3 − C2) and the persona effect (C1 − C3):

- Paired per-puzzle differences in absolute error (for MAE), signed error (for bias) and within-puzzle SD, each tested with the two-sided Wilcoxon signed-rank test over the 100 puzzles. The mean difference is reported as the effect size. Holm correction over the two contrasts, per measure.
- ρ for each condition against zero with its p-value. The ρ difference between conditions is reported as a value only, since a test of it would need several hundred puzzles (Section 5).
- **Persona check (primary, position-matched).** Bold and `neutral_1` are called first, Cautious and `neutral_2` second. Under the parallel protocol neither sees the other's advice of the round, so C3's gap is the difference two advisors with one shared instruction show by chance. Each advisor gets a non-candidate share per game (suggestions after turn 1). For each puzzle, the mean per-game difference second minus first speaker is taken in C1 (Cautious − Bold) and in C3 (`neutral_2` − `neutral_1`). A two-sided Wilcoxon signed-rank test over the puzzles in both conditions tests C1's difference minus C3's. The personas count as working if it is significant with C1's difference larger. Position and exposure are the same in both conditions, so what remains is the persona text. Puzzles are the unit, as in the outcome contrasts.
- **Descriptive persona tests.** `cautious_vs_bold` (Wilcoxon on per-game Cautious − Bold in C1) and `advisor_difference` (Friedman across the advisors of a condition) stay in `metrics.json`. They treat games as independent, although each puzzle is played 10 times, so they are not used for the verdict.
- **Same-word share (descriptive, formerly herding).** For each advisor, the share of its dissents (suggestions that differ from the GM's proposal) that name the same word as an earlier-called advisor's dissent in that round. Under the parallel protocol the advisors cannot see each other, so this measures how often independent advisors agree on an alternative. Reported in `persona_stats.csv` (`dissents`, `dissent_copies`, `herding_share`). Under the sequential protocol in the first F7 smoke runs it was Cautious 1 of 99, Casual 9 of 43, `neutral_2` 17 of 20 and `neutral_3` 21 of 23, which motivated the switch.
- Implemented at F5 and F6 in `persona_stats.py`, `nonparametric.py` (stdlib Wilcoxon and Friedman, checked against scipy) and `analysis_final.py`.

**Implemented at F6** as `experiment/analysis_final.py`. The constant-guess baseline is the MAE of predicting every puzzle at the human mean of the puzzles at hand (`constant_baseline_mae`). Next to it, `bias_corrected_mae` removes the condition's own bias, so a value below the baseline shows puzzle-level information beyond a constant shift. A fingerprint warning is written when the conditions ran on more than one `system_fingerprint`. Run after F9:

```bash
uv run python -m multi_agent_testing.experiment.analysis_final \
  --c1 experiments/final-c1 --c2 experiments/final-c2 --c3 experiments/final-c3 \
  --output-dir experiments/final-analysis
```

**Sensitivity checks.** Quartiles instead of terciles, missing games scored as losses, the 7-bin distribution pooled by tercile, and the cost and reliability of each condition (tokens, seconds, calls, repairs and failures per game).

### 7.1 Limitations stated in the thesis

The final study uses two ablations, C2 (no debate) and C3 (no personas). Other design choices are not ablated. They are stated as limitations, with the evidence the study collects for each.

| Limitation | Evidence or control |
|---|---|
| The final protocol (parallel) differs from the pilot's (sequential), so the pilot's persona results are not a direct preview of the final ones. | Both protocols are recorded; the pilot can be rerun with `--debate-protocol sequential`. |
| Advisors still see the previous rounds, so they can influence each other across rounds, and the GM sees the advisors in a fixed order. | The same-word share is reported per advisor and condition. |
| C1 − C3 removes three things at once: playstyle content, advisors that differ from each other, and persona names the GM can weigh. | The position-matched check shows whether the persona text changes behaviour. It cannot split the outcome effect. |
| C3 − C2 also differs in compute (about 37 against 4 calls per game). | Calls, tokens and seconds per game are reported per condition. |
| The neutral C3 prompt was revised after the first smoke test, while the persona text was not. | Recorded with its reason in Sections 2.2 and 6.4. |
| One model, one game, zero-shot prompts, and a debate protocol designed for this study. | Scope of the thesis. |

## 8. Implementation phases

### Phase table

| Phase | Goal | Main tasks | Done when | Mode | Size |
|---|---|---|---|---|---|
| **F0** Decisions | Fix what cannot change after the runs start | Confirm the RQ wording and the role of the baselines (Section 3), the C2 and C3 instruction drafts, terciles as the category scheme and the budget with the supervisor. Update the roadmap, README and CLAUDE.md scope line. | The decisions are recorded in Section 1 and the docs no longer say "no single-agent condition". | offline | S |
| **F1** Terciles | Freeze the category cut-points | Add a rank-based tercile split next to `quartiles.py`, written to `src/data/processed/terciles.json`. | Group sizes differ by at most one, the cut-points are 4.07 and 4.42, and a test checks the mapping rule. | offline | S |
| **F2** Manifests | Select the final and smoke puzzles | Extend the manifest tool with a single stratified draw (33/33/34 per tercile, seed `20261103`) that excludes all pilot manifests. Write the 8-puzzle smoke manifest from the pilot-02 wide manifest. | `final.csv` (100 rows) and `final-smoke.csv` (8 rows) exist, and tests confirm no overlap with any pilot manifest and identical output on a re-run. | offline | S |
| **F3** Single-agent mode | Support C2 | Allow a line-up without advisors, in which one decision per turn is validated and played. Add the `solo_player` persona and its preset. | Scripted tests cover a full solo game, its repair path and its call count (one call per turn without repairs). | offline | M |
| **F4** Neutral preset | Support C3 | Add `neutral_advisor` under three keys and a preset that pairs them with the neutral GM. | The preset builds three advisors with identical instructions, and the pilot-02 registry text is unchanged (`personas_test`). | offline | S |
| **F5** Statistics for all conditions | Log comparable turn statistics | Make `turn_statistics` and `persona_stats` work without advisors (C2) and with neutral keys (C3). Add the per-game persona tests (Wilcoxon for Cautious − Bold, Friedman across advisors). | Scripted tests cover all three conditions, and a test confirms the answer word never appears in any prompt in any condition. | offline | M |
| **F6** Final analysis | Per-condition metrics and paired contrasts | Add `analysis_final.py` (Section 7), terciles, the ICC F-intervals and the Holm-corrected Wilcoxon contrasts. | Tests on synthetic runs reproduce known values, and the module writes `metrics.json`, `condition_summary.csv`, `contrasts.csv` and `persona_stats.csv` (plus `puzzle_summary.csv` and `runs.csv` for F11). | offline | M |
| **F7** Smoke tests | Measure C2 and C3 before freezing | Play the smoke manifest × 2 games in each condition (48 games, under $1). Read one transcript per condition. | At least 15 of 16 games complete per condition, the neutral advisors argue without playstyles, and the measured cost per game replaces the estimates in Section 6.3. | live (tiny) | S |
| **F8** Freeze | Lock the final configuration | Record the model, snapshot, settings, personas, prompts, hashes and code revision in Section 6.1. Tag `final-frozen`. | The tag exists, and nothing in Sections 1, 2 or 6 changes after it. | offline | S |
| **F9** Run | Collect the 3,000 games | C1, C2 and C3 in parallel, 4 workers each (Section 6.2). | 100 × 10 completed games per condition, or failures documented. | live (~16 h) | L |
| **F10** Analysis | Produce the results | Run `analysis_final.py` on the three directories. | `metrics.json` and the CSVs exist in `experiments/final-analysis`. | offline | S |
| **F11** Figures | Visualize the results | Extend `plots.py` with per-condition panels and contrast plots, read only from the analysis outputs. | All figures exist as PDF and PNG and pass a visual check. | offline | M |
| **F12** Findings | Close the study | Write the findings into the roadmap and the thesis results chapter. | The results are recorded with the deviations from this plan. | offline | S |

### Checkpoints

- **After F6:** all code is done and tested offline. Review the diff before spending any tokens.
- **After F7:** go or no-go on C2 and C3. If C3's advisors drift into playstyles or C2 fails often, revise the drafts and repeat F7 before F8.
- **After the first chunk of each condition in F9:** check the fingerprints, the failure rate and the spend before continuing.

## 9. Open questions for the supervisor
- **Decided on 2 November 2026: the final study uses the parallel protocol (Section 2.0).** The C1 and C3 smoke tests are rerun under it (F7), then the configuration is frozen again (F8). The method chapter must describe the change from the pilot's sequential protocol.
- *Superseded:* the order ablation and the order and herding limitations were discussed for the sequential protocol. With the parallel protocol (Section 2.0) the advisors of a round no longer see each other, so the order ablation was dropped (decided on 2 November 2026).

- RQ3 in the thesis (expert evaluation) against persona behavior here, and whether C2 and C3 as baselines inside RQ1 to RQ3 are enough without a separate comparison question.
- Whether terciles replace quartiles as the category scheme of the final study.
- Whether the C2 instruction should name a playstyle at all. The draft gives none, so C2 stays a generic player.
- Whether the expert evaluation of the thesis uses games from this study, and from which condition.
