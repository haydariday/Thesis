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
| Model | `glm-5.3-flash` on OpenCode Zen through the chat-completions protocol (`temperature`-capable). |
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

- **Model:** `glm-5.3-flash` ($0.15 input / $0.50 output per 1M tokens, `https://opencode.ai/zen/v1/chat/completions`), according to the [OpenCode Zen model list](https://opencode.ai/docs/zen/). A one-call probe must confirm that it accepts `temperature` and returns usage before any runs. If it fails, the probe moves to the next cheap chat model on the list (`deepseek-v4-flash`).
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

## 9. Implementation phases

The work is split into 16 small phases (P0 to P15). Each phase ends in one commit on `pilot-2`, has a clear "done when" check, and can be reviewed on its own. Phases marked **offline** use no API calls. Phases marked **live** spend tokens.

### Track overview

```text
Gate          P0 decisions
Data track    P1 clean 7-bin data -> P2 quartiles + F1 -> P3 manifests
Persona track P4 registry -> P5 dynamic graph -> P6 CLI/config -> P7 instrumentation
Live check    P8 probe + smoke game -> P9 freeze config
Runs          P10 Exp B wide -> P11 Exp A deep
Analysis      P12 RQ1/mean/quartile -> P13 distribution + persona -> P14 figures F2-F9
Write-up      P15 findings + final sizing
```

The data track and the persona track are independent, so they can be done in either order. P12 to P14 can be written and tested on synthetic run files while P10 and P11 are running.

### Phase table

| Phase | Goal | Main tasks | Done when | Mode | Size |
|---|---|---|---|---|---|
| **P0** Decisions | Fix the choices that cannot change after runs start | Choose the temperature (Section 6) and the RQ1 equivalence tolerance. Confirm the RQ2 wording change with the supervisor. | Both values are written in Section 1 and the README. | offline | S |
| **P1** Clean human data | Turn `individual` into a 7-bin distribution | Add `experiment/human_data.py`, reusing `manifest.audit_record`. Write `p1 … p7`, `human_mean` and its low/high bounds, `sample`, notes and a duplicate-answer flag. | `src/data/processed/wordle_human_clean.csv` exists with 1,865 rows (1,861 eligible), and tests check that each row's bins sum to 1 and that the means match `manifest.py`. | offline | S |
| **P2** Quartiles and F1 | Define D1–D4 and check them visually | Rank-based split into four groups of equal size. Save the cut-points to `quartiles.json`. Create `experiment/plots.py` with figure F1 only. | Group sizes are 465/465/465/466, the cut-points are about 3.98, 4.24 and 4.53, and F1 renders cleanly as PDF and PNG. | offline | S |
| **P3** Manifests | Select the pilot-02 puzzles | Stratified sampling by quartile with seeds `20261013` (deep, 3 per quartile) and `20261014` (wide, 12 per quartile). Exclude pilot-01 puzzles and duplicate answers. Keep the two sets disjoint. | `pilot-02-deep.csv` (12 rows) and `pilot-02-wide.csv` (48 rows) exist, and a test confirms no overlap and identical output on a re-run. | offline | S |
| **P4** Persona registry | Make personas data, not code | Add `PersonaSpec`, `PERSONAS` and `PRESETS`, and move the existing GM, Negative and Positive into the registry. Add Bold, Cautious and Casual. `create_agents(preset=…)` returns the GM and an ordered advisor list. | The `pilot-01` preset builds the same agents and instructions as before, and the current tests pass unchanged. | offline | S |
| **P5** Dynamic debate graph | Allow any number of advisors | `sequential.py` builds one node per advisor. Replace `alternative` with `suggestions`. Apply `action_rule` checks for each persona. The GM review prompt lists every suggestion. | `debate_flow_test` passes for `pilot-01` (2 advisors, same call counts as before) and for `pilot-02` (3 advisors). | offline | M |
| **P6** CLI and config wiring | Choose personas without editing code | Add `--persona-preset` and `--advisors` to the runner and to `debate_test`. Write the chosen keys and full instructions into `experiment_config.json` and each run's metadata. | A scripted-backend run records `bold, cautious, casual` in its config and metadata. | offline | S |
| **P7** Turn instrumentation | Log the GM and persona statistics | Add `initial_proposal`, `gm_retained`, `advisor_suggestions`, `adopted_from`, `advisor_agreed`, `is_candidate` and `candidates_remaining` (Section 2.3). Candidate checks use public feedback only. | Scripted tests cover retain, adopt and agree cases, and a test confirms that the answer word never appears in any prompt. | offline | M |
| **P8** Probe and smoke game | Confirm the model works end to end | One call to `glm-5.3-flash` with `temperature`, checking usage and the returned model ID. Then play one full game with the `pilot-02` preset. | The probe JSON and one completed run JSON are saved, and a manual read of the transcript shows each persona arguing in character. Fall back to `deepseek-v4-flash` if the probe fails. | live (tiny) | S |
| **P9** Freeze configuration | Lock pilot-02 | Record the model, the returned snapshot, the temperature, the personas, the prompts, the hashes and the code revision. Tag the commit `pilot-02-frozen`. | The tag exists, and nothing in Section 1 or 6 changes after it. | offline | S |
| **P10** Run Exp B (wide) | Collect the mean-alignment and quartile data first | 48 puzzles × 3 runs = 144 games, run in chunks with `--max-seconds` and resume. It goes first because it is shorter and gives an early check of the personas. | 48 × 3 completed games, or failures documented under the replacement policy. | live (~5 h) | M |
| **P11** Run Exp A (deep) | Collect the RQ1 and distribution data | 12 puzzles × 32 runs = 384 games, in chunks with resume. | 12 × 32 completed games, or failures documented. | live (~13 h) | L |
| **P12** Analysis: RQ1, mean, quartile | Core metrics | Add `analysis_pilot02.py`, reusing the `analysis.py` helpers: within-puzzle SD, ICC(1,1) and ICC(1,k), MAE, signed error, Spearman, Pearson, the 4×4 confusion matrix, quadratic-weighted kappa and bootstrap CIs. | Tests on synthetic runs reproduce known values, and the module produces `metrics.json` and `puzzle_summary.csv`. | offline | M |
| **P13** Analysis: distribution and persona | Supervisor's comparison and persona statistics | W1, JSD, TVD and chi-square for each puzzle, bootstrap CIs over runs and the split-half W1. Also GM retention and advisor adoption, agreement and non-candidate shares. | Hand-checked synthetic cases pass, and the module writes `distribution_summary.csv` and `persona_stats.csv`. | offline | M |
| **P14** Figures F2–F9 | Visualize every result | Add F2–F9 to `plots.py`, reading only the analysis outputs. Re-plot pilot-01 with F2, F5, F6 and F7 for comparison. | All figures exist as PDF and PNG at IEEE widths and pass a visual check for clipping, overlap and contrast. | offline | M |
| **P15** Findings and final sizing | Close pilot-02 | Write a pilot-02 findings section in the roadmap. Use the observed variance to size the final study (runs per puzzle and puzzles per quartile). | The roadmap is updated, and the final-study sizes are recorded before any final run. | offline | S |

### Checkpoints

- **After P7:** all code changes are done and tested offline. Review the diff before spending any tokens.
- **After P8:** a go/no-go decision on the model and the persona behavior.
- **After P10:** a quick look at the persona statistics. If Bold and Cautious do not differ in their non-candidate share, fix the prompts and repeat P8 and P9 before running P11. Any wide games already played then belong to a different configuration and must be reported separately.

## 10. Open questions for the supervisor

- Temperature: favor consistency (low) or player-like spread (high)? See Section 6.
- RQ2 wording change to include guess-count distributions and quartiles (Section 4).
- Whether a GM personality should become RQ3 in a later study.
