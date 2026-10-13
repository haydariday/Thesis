# Pilot-02 Plan: Playstyle Personas, Distribution Comparison and Difficulty Quartiles

Drafted: 13 October 2026. Status: plan only. No code has been changed yet.

Pilot-02 replaces the Negative/Positive advisors with playstyle personas. It also adds the supervisor's 7-bin distribution comparison and a D1–D4 quartile test. RQ1 and RQ2 keep their current wording. Every new measurement is placed under one of them, and the scope still has no single-agent condition.

## 1. Decisions recorded

| Topic | Decision |
|---|---|
| Personas | Bold and Cautious are required advisors. Casual is an optional third advisor and is turned on for pilot-02. |
| GM | Stays neutral in pilot-02. A GM personality is future work, possibly an RQ3, and pilot-02 logs the statistics it would need. |
| Supervisor's 7-bin advice | Compare the system's guess-count distribution with the human distribution for each puzzle (bins 1–6 plus 7 = fail). |
| D1–D4 test | "Play, then map": the system plays the puzzle, and its mean score is placed into a quartile using the human cut-points. The model never rates difficulty directly. |
| Human data | Standard mode only. The `hardmode` block is not used. |
| Model | A new model that accepts `temperature`, served by OpenCode Zen through the chat-completions protocol. |
| Distribution pilot size | 32 runs × 12 puzzles, which gives the Thompson ±20% precision level (see Section 5). |

## 2. Personas (modular)

### 2.1 Design

Personas move from hard-coded agents to a registry plus a configuration list, so a persona can be added, removed or reordered without editing the debate graph.

```text
agent/personas.py
  PersonaSpec(key, display_name, slot, instruction, task, action_rule)
      slot:        "gm" | "advisor"
      action_rule: "any" | "must_differ" | "must_equal"   (kept for the pilot-01 personas)
  PERSONAS = {neutral_gm, negative, positive, bold, cautious, casual}
  PRESETS  = {
      "pilot-01":        gm=neutral_gm, advisors=[negative, positive],
      "pilot-02":        gm=neutral_gm, advisors=[bold, cautious, casual],
      "pilot-02-core":   gm=neutral_gm, advisors=[bold, cautious],
  }
  create_agents(backend, preset=... | gm=..., advisors=[...])
```

- **CLI and config:** `--persona-preset pilot-02` or `--advisors bold,cautious,casual`. The chosen keys and the full instruction text are written into `experiment_config.json` and each run's metadata.
- **Debate graph:** `orchestra/flow/sequential.py` builds one node per advisor from the list, in order (`gm_propose → advisor_1 → … → advisor_n → gm_review`). The routing policy and the `max_rounds` cap stay the same.
- **State:** `alternative: str` becomes `suggestions: {advisor_key: action}` for the current round. The GM review prompt shows every advisor's suggestion and reason.
- **GM slot:** the GM is also read from the registry, so a GM persona can be swapped in later without changing the graph.
- **Compatibility:** the `pilot-01` preset reproduces the old Negative/Positive behavior, so pilot-01 can still be re-run.

### 2.2 Persona instructions

| Persona | Slot | Playstyle | Instruction (draft, from the persona suggestion note) |
|---|---|---|---|
| Bold | advisor (required) | Exploit: plays to win now | Prefers guesses that could still be the answer. Critiques the GM's proposal from this view and suggests a better candidate answer if one exists. Accepts the risk of using more guesses later. |
| Cautious | advisor (required) | Explore: plays not to lose | Prefers guesses that rule out the most remaining letters, even if the guess cannot be the answer. Suggests a more informative guess if one exists. Its priority is never losing. |
| Casual | advisor (optional) | Everyday player | Plays like a typical daily player. Prefers common, familiar words and a habitual opener, and does not compute letter statistics. |

Advisors use `action_rule = "any"`. That means an advisor may agree with the GM by returning the same word, which is recorded as agreement rather than rejected.

### 2.3 New per-turn instrumentation

These fields are logged in every turn record. They feed the persona statistics now and a possible GM-persona RQ later.

| Field | Meaning |
|---|---|
| `initial_proposal` | The GM's first proposal in the turn. |
| `final_action` | The executed guess. |
| `gm_retained` | `final_action == initial_proposal`. |
| `advisor_suggestions` | Each advisor's suggestion and round. |
| `adopted_from` | The advisors whose suggestion equals the final action when it differs from the initial proposal. |
| `advisor_agreed` | Whether each advisor returned the GM's proposal unchanged. |
| `is_candidate` | For each suggestion and the final action, whether the word is still consistent with all public feedback, meaning it could still be the answer. This is computed from public history only. |
| `candidates_remaining` | The number of vocabulary words still consistent with the feedback before the turn. |

Aggregated per experiment, these give:

- **GM retention rate:** the share of turns where the GM keeps its own proposal.
- **Advisor adoption rate:** for each advisor, the share of turns where the GM takes that advisor's word.
- **Advisor agreement rate:** for each advisor, the share of turns where it simply agrees with the GM.
- **Non-candidate share for each advisor (manipulation check):** the Cautious share should be clearly above the Bold share. If it is not, the persona prompts are not working and the method chapter must say so.

## 3. Human data cleaning

A new module, `experiment/human_data.py`, reuses the eligibility rules in `manifest.py` and writes `src/data/processed/wordle_human_clean.csv`.

### 3.1 Converting `individual` to 7 bins

`individual` holds whole-number percentages of players who solved in 1 to 6 guesses. No row sums to exactly 100: the maximum is 99, and the remainder is the share of players who failed.

```text
p_k      = individual[k] / 100           for k = 1..6
p_7      = (100 - sum(individual)) / 100 # fail share, scored as 7
human_mean = sum(k * p_k for k in 1..7)
```

Each row stores `p1 … p7`, `solved_share`, `human_mean`, `human_mean_low` and `human_mean_high` (±3-point rounding bounds, as in pilot-01), `sample`, `quartile` and `eligibility_notes`.

### 3.2 Eligibility (current rules, verified on 13 October 2026)

- 1,865 rows, of which 1,861 are eligible. Excluded: 620 MOOSE (all-zero distribution), 625 PINKY (missing sample), 1502 (num mismatch) and 1273 (quarantined).
- High-failure rows such as 454 PARER (59% fail), 1426 EAGER, 491 MUMMY and 712 JAZZY are real hard puzzles, not data errors. They stay in, because they form the hard tail that pilot-01 lacked.
- 26 answers appear twice. Both copies stay in the clean file, but only puzzles with a unique answer can be sampled, so the model never sees the same answer word twice.
- The 20 pilot-01 puzzles are excluded from pilot-02 sampling.
- This leaves a sampling pool of 1,789 puzzles.

### 3.3 D1–D4 quartiles

Eligible puzzles are sorted by `(human_mean, puzzle_id)` and split into four groups of equal size. Rank-based splitting keeps the groups equal even when means tie.

| Quartile | Puzzles | Human mean range | Puzzles with ≥5% fail |
|---|---:|---|---:|
| D1 (easiest) | 465 | 3.30 – 3.98 | 1% |
| D2 | 465 | 3.98 – 4.24 | 1% |
| D3 | 465 | 4.24 – 4.53 | 18% |
| D4 (hardest) | 466 | 4.53 – 6.21 | 83% |

The cut-points (about 3.98, 4.24 and 4.53) are frozen in the config before any runs. The old easy/hard line at 4.0 is almost exactly the D1 boundary, which means 75% of puzzles were labelled "hard" under the old rule. This is a strong argument for the quartile scheme.

## 4. Experiment structure: why RQ1 and RQ2 are split

RQ1 asks how repeatable the outcome is on the same puzzle, so it needs many runs on a few puzzles. RQ2 asks how well the system matches humans across puzzles, so it needs many puzzles. The supervisor's distribution comparison is an exception, because it needs many runs per puzzle. Each experiment is therefore sized for its own question.

| | Exp A: deep | Exp B: wide |
|---|---|---|
| Purpose | RQ1 consistency and the RQ2 distribution comparison | RQ2 mean alignment and RQ2 D1–D4 agreement |
| Puzzles | 12 (3 per quartile) | 48 (12 per quartile) |
| Runs per puzzle | 32 | 3 |
| Games | 384 | 144 |
| Sampling | Stratified random by quartile, seed `20261013` | Stratified random by quartile, seed `20261014`, disjoint from Exp A |
| Output dir | `experiments/pilot-02-deep/` | `experiments/pilot-02-wide/` |

Both experiments use one frozen configuration (model, temperature, personas and prompts), so results can be pooled where that makes sense. For example, Exp A's 12 puzzles can join Exp B's mean-alignment analysis as a robustness check, but they are reported separately.

### Where the D1–D4 test belongs (question 3C)

It belongs under **RQ2**. RQ2 already asks about agreement with human difficulty "using average guess scores and easy/hard categories". D1–D4 replaces easy/hard as the categorical measure. This needs no new RQ, only a wording change in RQ2: "… measured using average guess scores, guess-count distributions and difficulty quartiles".

## 5. Sample-size justification

### 5.1 Runs per puzzle (Exp A)

Each puzzle's outcome is a multinomial over 7 bins. Thompson (1987) gives the sample size that keeps all bin proportions within ±d of their true values at the same time, with 95% confidence:

| Margin d | Runs per puzzle |
|---|---:|
| ±5% | 510 |
| ±10% | 128 |
| ±20% | 32 |

Sources: Thompson's table as reproduced by [NOAA Fishery Bulletin](https://spo.nmfs.noaa.gov/sites/default/files/pdf-content/2007/1051/gerritsen.pdf) and [Kim et al., blinding sample size](https://escholarship.org/content/qt698123b3/qt698123b3_noSplash_a9a2ecb3dda8e3040319daa55d83eeb7.pdf).

As a cross-check, a chi-square goodness-of-fit test against the human distribution (df = 6, α = 0.05, power 0.8) needs 55 runs to detect a large difference (Cohen's w = 0.5) and 152 runs for a medium one (w = 0.3). These figures are my own calculation with the noncentral chi-square distribution.

Pilot-02 uses **32 runs (±20%)**. That is enough to see the shape of each distribution and to measure the system's real spread and cost, but not enough for final claims. The final run count is set from pilot-02's observed variance.

### 5.2 Puzzles for D1–D4 (Exp B)

The estimand is the share of puzzles placed in the correct quartile, which is a proportion. Cochran's formula with p = 0.5, a finite-population correction (N = 1,789) and equal allocation across four strata gives:

| Margin | Total puzzles | Per quartile |
|---|---:|---:|
| ±5% | 317 | about 80 |
| ±10% | 92 | 23 |

For the pilot, [Julious (2005)](https://onlinelibrary.wiley.com/doi/abs/10.1002/pst.185) recommends 12 per group, so pilot-02 uses **48 puzzles (12 per quartile)**. Three runs per puzzle keep the per-puzzle mean reliable: pilot-01 had ICC(1,3) = 0.83.

## 6. Model and frozen configuration

- **Model:** a temperature-capable chat-completions model on OpenCode Zen. The current candidate is `deepseek-v4-flash` ($0.14 input / $0.28 output per 1M tokens, chat completions), according to the [OpenCode Zen model list](https://opencode.ai/docs/zen/). A one-call probe must confirm that it accepts `temperature` and returns usage before any runs. If it fails, the probe moves to the next cheap chat model on the list.
- **Temperature (decision needed):** a low temperature (0.2, as in pilot-01) favors RQ1 consistency but narrows the system's distribution, which makes the RQ2 distribution comparison almost meaningless. A higher value (for example 1.0) treats each run as one simulated player. This choice must be made and recorded before the runs, ideally with the supervisor.
- **Unchanged from pilot-01:** `max_rounds=3`, non-streaming, `max_repairs=1`, `request_timeout=300`, `api_retries=1`, `max_attempts_per_unit=2`, and the vocabulary and dataset hashes.
- **Cost estimate:** with three advisors a turn has five calls instead of four, so about 119 s and 18k tokens per game. Exp A and Exp B together come to about 528 games, 17–18 hours and 9.5M tokens. The real speed depends on the chosen model.

## 7. Analysis

A new `experiment/analysis_pilot02.py` reads both experiment directories and writes CSV and JSON outputs. Like the current `analysis.py`, it uses only the standard library.

### RQ1 (Exp A)

- Within-puzzle SD of the penalized score, ICC(1,1) and ICC(1,32).
- Pairwise exact-match rate and mean pairwise absolute difference.
- Split-half stability of the distribution: Wasserstein distance between runs 1–16 and runs 17–32 of the same puzzle.
- An equivalence check against a tolerance fixed before the run (for example, within-puzzle SD ≤ 0.5).

### RQ2 distribution comparison (Exp A)

For each puzzle, compare the system's 7-bin distribution (32 runs) with the human `p1 … p7`:

- **Primary: Wasserstein-1 (earth mover's) distance on ordinal bins**, \( W_1 = \sum_{k=1}^{6} |F_{sys}(k) - F_{hum}(k)| \). The bins are ordered, so moving mass from 3 to 4 counts as less wrong than moving it from 3 to 7.
- **Secondary:** Jensen-Shannon divergence, total variation distance and a chi-square goodness-of-fit statistic against the human distribution.
- 95% bootstrap CIs, resampling runs within each puzzle.
- Signed shift: the system's mean minus the human mean, plus the difference in fail share.

### RQ2 mean alignment and D1–D4 (Exp B, with Exp A as a check)

- MAE, signed error, Spearman and Pearson between system and human means.
- The system mean is mapped to D1–D4 using the frozen human cut-points, which gives a 4×4 confusion matrix.
- Exact quartile accuracy, adjacent accuracy (within one quartile), quadratic-weighted Cohen's kappa and per-quartile recall.
- Bootstrap CIs at the puzzle level, stratified by quartile.
- Expected risk: pilot-01 showed the system is about 0.49 guesses better than humans, so many puzzles may collapse into D1–D2. That pattern should be reported as a finding rather than hidden.

### Persona and GM statistics (both experiments, descriptive)

GM retention rate, adoption rate for each advisor, agreement rate for each advisor, non-candidate share for each advisor (the manipulation check), and the termination mix (`gm_stop` versus `max_rounds`).

### Reliability (supporting)

Invalid-output and repair-exhaustion counts, backend errors, and token and latency distributions with measurement coverage.

## 8. Data visualization

A new `experiment/plots.py` builds every figure from the analysis CSV and JSON files, never from raw logs, so figures always match the reported numbers. It uses matplotlib, added as an optional `viz` dependency group so the core package stays light.

Output goes to `experiments/pilot-02-*/figures/` as both PDF (vector, for the paper) and PNG (for slides and notes). Figures are sized for IEEE columns (3.5 in single, 7.16 in double), use a colorblind-safe palette and set fonts large enough to read in print. The command is `python -m multi_agent_testing.experiment.plots --experiment-dir …`.

| Figure | Content | Supports |
|---|---|---|
| F1 Human difficulty | Histogram of human means with the D1–D4 cut lines, plus the mean 7-bin distribution for each quartile as stacked bars | Data chapter, quartile definition |
| F2 Run-to-run spread | Strip or box plot of the 32 scores for each Exp A puzzle, ordered by human mean, with the human mean marked | RQ1 |
| F3 Distribution comparison | 12 small panels, one per Exp A puzzle, each with paired human and system bars over bins 1–7 and the W1 value in the corner | RQ2 distribution |
| F4 Distance forest plot | W1 with its bootstrap CI for each puzzle, grouped by quartile | RQ2 distribution |
| F5 Mean alignment | Scatter of system mean against human mean with the y = x line and quartile cut lines, colored by human quartile | RQ2 mean |
| F6 Bland-Altman | Difference (system − human) against the average of the two, with bias and limits of agreement | RQ2 mean, shows the systematic "easier than human" bias |
| F7 Quartile confusion | 4×4 heatmap of human quartile against system quartile, with counts and row percentages | RQ2 D1–D4 |
| F8 Persona behavior | Bars of GM retention, the adoption rate for each advisor and the non-candidate share for each advisor | Persona manipulation check, future GM RQ |
| F9 Cost and reliability | Distributions of tokens and seconds per game, plus failure counts | Supporting measurements |

Pilot-01 can be re-plotted with F2, F5, F6 and F7 (using easy/hard or quartiles) so that the two pilots can be compared visually.

## 9. Work list (to implement after this plan is approved)

1. `human_data.py`: produce the clean 7-bin CSV and quartile cut-points, with tests.
2. Persona registry, presets, CLI flags and the dynamic advisor nodes in the debate graph. Keep a `pilot-01` preset and update the existing tests.
3. Per-turn instrumentation (Section 2.3) in `play.py` and `run_log.py`.
4. Pilot-02 manifests (`pilot-02-deep.csv`, `pilot-02-wide.csv`) built with stratified quartile sampling and recorded seeds.
5. Model probe: confirm that `temperature` is accepted and that usage is reported.
6. Decide and record the temperature and the RQ1 equivalence tolerance before running anything.
7. Run Exp A and Exp B with the existing resumable runner.
8. `analysis_pilot02.py` (Section 7) and `plots.py` (Section 8).
9. Write a pilot-02 findings section in the roadmap and decide the final-study sizes from the observed variance.

## 10. Open questions for the supervisor

- Temperature: favor consistency (low) or player-like spread (high)? See Section 6.
- RQ2 wording change to include guess-count distributions and quartiles (Section 4).
- Whether a GM personality should become RQ3 in a later study.
