# Wordle Multi-Agent Playtesting: Research Context and Experiment Roadmap

Updated: 8 October 2026.

This README records the current conference-paper scope and the work needed to obtain defensible results from the Wordle playtesting app. It is an experiment plan and context handover, not a claim that the implementation or evaluation is complete.

## Current scope

- **Game:** Wordle only.
- **System:** Persona-based multi-agent debate orchestrated with LangGraph.
- **Agents:** Game Master, Negative Advisor, and Positive Advisor.
- **Evaluation:** Repeated-run consistency and agreement with human difficulty.
- **Excluded:** Single-agent comparison, expert-evaluation RQ3, and Slay the Spire from this conference study.
- **Supporting measurements:** Token usage, elapsed time, invalid outputs, retries, infrastructure failures, and debate termination behavior (`gm_stop` vs `max_rounds`, with the round each debate ended; descriptive only).

This is a system-validation study. It does not establish that multi-agent debate outperforms a single agent or that any particular persona causes the observed performance. Changes to the approved thesis scope should be confirmed with the supervisor; the conference scope need not replace the whole thesis scope.

## Research questions

### RQ1: Outcome consistency

> How consistent are the Wordle playtest outcomes produced by a persona-based multi-agent debate system across repeated runs on the same puzzles?

Evaluate per-puzzle variability in penalized guess scores and win rates. Consistency must be interpreted alongside performance: consistently losing is not evidence of useful playtesting.

### RQ2: Human difficulty alignment

> To what extent do the Wordle difficulty estimates derived from the multi-agent system's playtest outcomes agree with human difficulty, measured using average guess scores and easy/hard categories?

Evaluate absolute score agreement, relative difficulty alignment, and category agreement. Human performance is the reference baseline; there is no single-agent comparison in this scope.

## Architecture and repository context

The user's step-by-step implementation uses the package `multi_agent_testing`. The separate `phase1-mas/` directory in this Project contains the earlier starter implementation using `thesis_debate`; it should not be mistaken for a verified copy of the current local app.

The current local structure (verified 8 October 2026 via `find src -type f`):

```text
src/
├── multi_agent_testing/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── agent_role.py
│   │   ├── backend.py
│   │   └── personas.py
│   ├── decision.py
│   ├── games/wordle/              # no __init__.py (namespace packages)
│   │   ├── bridge.py
│   │   ├── dataset.py
│   │   └── engine.py
│   ├── orchestra/
│   │   ├── debate.py
│   │   ├── debate_context.py
│   │   └── flow/
│   │       └── sequential.py
│   ├── run_log.py
│   └── test/
│       ├── debate_test.py         # --play / --debate entry point
│       ├── wordle_dataset_test.py
│       └── wordle_engine_test.py
└── data/
    ├── processed/                 # empty, reserved for cleaned outputs
    └── raw/
        ├── worldepuzzles.json    # actual filename (typo preserved)
        ├── allowed_guesses.txt
        └── worldepuzzles.diagnostic.md
```

Notes: there is no `backend_test.py` (only a stale `__pycache__` entry); `games/`, `orchestra/`, and `test/` have no `__init__.py`. Preserve `worldepuzzles.json` as the actual filename unless deliberately renaming it everywhere.

### Decision flow

```text
Public Wordle state
    → Game Master proposes a guess
    → Negative Advisor challenges it and proposes an alternative
    → Positive Advisor evaluates/defends the current proposal
    → Game Master selects the action and decides whether to stop debating
    → Orchestrator either continues debate or finalizes
    → Wordle engine validates and executes one guess
    → Public feedback is returned
```

The debate-round cap belongs to the orchestrator, not the model-visible context. Ending debate does not end the Wordle game. The game ends only on a correct answer or exhaustion of six submitted guesses.

## Current status and known risks

Verified against the local repository on 8 October 2026 (working tree after commit `f5ca602`; engine and debate-flow test suites pass offline).

- **Verified working (code):** Agent personas, swappable model backend, structured decisions, LangGraph debate, both `gm_stop` and `max_rounds` exit paths, and bounded decision repairs. Offline sequence tests confirm invalid actions such as `"Guess AUDIO"` are rejected and repaired; repair exhaustion raises a catchable `ValueError`; invalid output never consumes a Wordle guess; and uncaught failures are saved as failed runs (`won: null`, not a loss).
- **Verified working (instrumentation, new):** Per-call records (role, attempt, rejection, error type, token usage, latency, returned model) and per-run counters (`agent_calls`, `rejected_responses`, `backend_errors`); token totals remain `null` when any call lacks usage instead of under-reporting.
- **Verified working (live):** Complete saved games with correct win/loss status: `runs/puzzle-0-test.json` (older code, solved in 4) and `runs/probe-space-bunny-free.json` (current code, solved in 3; 31,243 tracked tokens over 12 calls, zero rejections).
- **Stale evidence:** `runs/batch-smoke/` predates the repair loop; its logs show an uncaught invalid-action crash and an API timeout that the current code handles differently.
- **Verified missing:** Experiment manifest, resumable batch execution, human-score preparation, and aggregate analysis are no longer missing: `multi_agent_testing.experiment` now provides `manifest`, `runner`, `summary`, and `analysis` modules. The manifest tool audited 1,865 records, found 1,861 eligible, and selected 20 pilot puzzles (6 easy / 14 hard) deterministically with seed `20261008`.
- **Model availability (8 October 2026):** `space-bunny` returned upstream "Model is unavailable"; `space-bunny-free` served the instrumentation probe (12/12 calls with usage); the current models (`gpt-6-luna`, `gpt-6-sol`, `claude-sonnet-5-5`, `gemini-3.8-flash`, `gpt-5.5`) reject chat completions (`ModelProtocolUnsupported`) and require the Responses protocol. `gpt-6-luna` also rejects `temperature` (provider default recorded as `null`). The app now supports both protocols (`--protocol chat|responses`), and a live smoke completed a full luna game through the Responses backend. Returned model identity is recorded per call.

### Decisions recorded (8 October 2026)

- **Backend:** OpenCode Zen (`https://opencode.ai/zen/v1/`), key in the ignored `.env`. The app supports both protocols (`--protocol chat|responses`). Pilot model: `gpt-6-luna` via the Responses protocol; it rejects `temperature`, so the provider default is used and recorded as `null`. `space-bunny-free` remains the verified chat-protocol fallback. Final model selection deferred.
- **Pilot configuration:** `max_rounds=3`, non-streaming, `max_repairs=1`, `request_timeout=300`, `api_retries=1`, `repetitions=3`, `max_attempts_per_unit=2`; `temperature=0.2` for chat-protocol models, provider default (recorded as `null`) for `gpt-6-luna`, which does not accept `temperature`.
- **Human loss handling:** treat `100 - sum(individual)` as the unsolved share, with ±3-point rounding bounds recorded as `human_mean_low`/`human_mean_high`.
- **Runner:** package module (`multi_agent_testing.experiment.runner`) with resume; `batch_run.py` is superseded but kept for reference.

The dataset diagnostic reported missing IDs, repeated answer words, and an ID mismatch at record 1502. Quarantine suspect records until verified; do not silently relabel them. Distinguish puzzles by validated ID/date, not answer word alone.

## Pilot-01 findings (8-9 October 2026)

Pilot configuration: 20 puzzles × 3 repetitions, `gpt-6-luna` via the Responses protocol (provider-default sampling), `max_rounds=3`, non-streaming.

- **Pipeline:** 62 attempts produced 56 completed games, 2 interruptions, and 4 invalid-output (repair-exhaustion) failures. 17/20 puzzles reached the planned completed-run count; `629`, `1271`, and `1877` were excluded from the primary panel.
- **RQ1 (panel, 17 puzzles × 3 runs):** win rate 1.00 (56/56 overall; no losses). Mean per-puzzle SD of penalized score 0.52; pooled within-puzzle SD 0.67. Variance decomposition: ICC(1,1) = 0.62, ICC(1,3) = 0.83; 5/17 puzzles produced identical triples; 49% of run pairs matched exactly.
- **RQ2 (panel):** MAE 0.64 [0.41, 0.89], signed error -0.49 [-0.80, -0.17], Spearman 0.69 [0.23, 0.91], Pearson 0.73 [0.41, 0.89], balanced accuracy 0.73 [0.51, 0.93] (bootstrap 95% CIs).
- **Termination:** 191/191 debates ended `gm_stop`; 188 after the first review and 3 after a second; none reached the cap. With this model and prompt the round cap is inert (debate depth about 1), with no difference between easy and hard puzzles.
- **Ceiling effect:** every completed game was solved, using about 0.49 fewer guesses than the human baseline, with several puzzles at the 2-guess floor. This removes the win/loss axis from RQ1 and biases system labels toward "easier than human" (4 human-hard to system-easy versus 1 human-easy to system-hard).
- **Cost and time:** about 95 s and 14.3k tokens per completed game (802,915 tokens and 88 minutes of model time over 56 runs).

### Design implications: strengthening RQ1 and RQ2

> <u>**Don't chase "significance" here.**</u> With a saturated outcome (100% wins) the honest, high-impact claims are *characterization* (debate depth about 1, the ceiling, the failure modes) and *precision* (tighter confidence intervals and equivalence against a pre-registered margin), not a p-value.

Levers, in impact order:

1. **Restore variance in the outcome.** Include the human-hard tail so six-guess solves and occasional losses occur. This is the single highest-leverage change and also relieves the RQ2 ceiling.
2. **Raise repetitions for the final (3 to 5).** RQ1 is within-puzzle variability, so repetitions buy RQ1 precision while additional puzzles buy RQ2 precision.
3. **Use a variance decomposition.** Report ICC alongside within-puzzle SD and agreement rates rather than a single average SD.
4. **Frame RQ1 as equivalence.** Pre-register a tolerance (for example within-puzzle SD ≤ 0.5, or ≥ 80% exact triples) and test against it (TOST or CI versus margin). The pilot is already borderline, so choose the margin deliberately and before the final run.
5. **Report the reliability axis.** Invalid outputs (about 2% of calls), repair exhaustion (4 units in the pilot), backend errors (0), and latency/token variability.
6. **Pre-register** the estimand, tolerance, puzzle set, and repetition count before the final run.

Proposed final design, sized from pilot timings: 40 fresh puzzles stratified across the human range with hard-tail oversampling, × 5 repetitions = 200 games (about 5.3 hours and 2.9M tokens), which should narrow the MAE interval to roughly ±0.15.

### Optional mechanism / ablation study (not RQ1 or RQ2)

A debate-depth or temperature experiment answers a *mechanism* question, not RQ1 or RQ2 as written. Two framings are possible: (a) a pre-registered robustness check attached to RQ1/RQ2 (do the conclusions hold under depth 1 versus 3, or temperature 0.2 versus 1.0?), or (b) its own research question as a protocol ablation, which changes scope and needs supervisor sign-off. Two blockers for doing it now: with `gpt-6-luna` the round cap is inert, so a meaningful depth experiment must vary the review prompt rather than `max_rounds`; and `temperature` is unsupported for luna, so a temperature experiment forces a single temperature-capable model (for example `gpt-5.4-mini`), confounding temperature with model identity.

For RQ1 impact, depth and temperature are second-order: on a saturated outcome (100% wins) neither adds the outcome variance RQ1 needs, so restore variance first (lever 1, hard-tail puzzles) and treat depth or temperature only as a pre-registered robustness add-on that checks whether the RQ1/RQ2 conclusions hold under a different setting.

## Difficulty and scoring definitions

### Continuous score is primary

Use human average guess score as the main difficulty measure. Prior LLM playtesting research uses average attempts and win rate as Wordle difficulty indicators, while explicitly distinguishing relative alignment from matching absolute human scores ([Xiao and Yang](https://arxiv.org/html/2410.02829v1)).

For each completed system game:

```text
Solved: score = submitted guesses used, from 1 to 6.
Lost after six guesses: score = 7.
API failure, invalid-output exhaustion, or interruption: no game score.
```

Seven is a loss penalty, not an actual seventh guess. This convention matches the documented treatment of unsolved games in the Engaging Data baseline; verify that the local dataset uses the same convention before comparing averages ([Wordle Stats](https://engaging-data.com/wordle-guess-distribution/)).

For puzzle `i`, calculate the system mean over its completed independent games. Always report the completed-run count, wins, losses, and infrastructure failures next to that mean.

### Secondary easy/hard classification

```text
Easy: average score < 4.0
Hard: average score >= 4.0
```

Apply this rule independently to the human average and the system average. Do not round first. These are study-specific operational labels, not universal difficulty categories.

Fix the threshold before inspecting final system results. Keep continuous scores primary and repeat classification analysis at 3.8 and 4.2 as sensitivity checks, not as replacement thresholds selected for better accuracy.

### Human-score preparation

- Select a single human game mode and document it; do not mix standard and hard-mode statistics.
- Prefer an authoritative supplied average when its calculation is known.
- If reconstructing from distributions, use `human_score = sum(k * p_k for k=1..6) + 7 * p_loss`, with probabilities on a 0–1 scale.
- Verify whether the dataset stores percentages or probabilities and whether bins refer to all plays or solved plays only.
- Do not treat rounding differences as definite losses. Flag missing or ambiguous loss proportions and document the reconstruction policy.
- The Engaging Data visualization rounds guess-distribution percentages to whole percentages, so averages reconstructed from those displayed bins are approximate ([Wordle Stats](https://engaging-data.com/wordle-guess-distribution/)).
- Keep human averages, labels, puzzle IDs, and secret answers out of agent prompts.

## What must be done to obtain results

### Milestone: Verify one complete game

- [ ] Complete one live game without an uncaught error.
- [ ] Confirm answer secrecy in every model-visible prompt.
- [ ] Confirm duplicate-letter feedback and six-guess termination.
- [ ] Verify supplied-vocabulary validation and document any extra policy, such as rejecting repeated guesses.
- [ ] Confirm invalid responses do not consume a Wordle guess.
- [ ] Verify both debate termination paths without showing the cap to agents.
- [ ] Save a completed JSON record and inspect it.
- [ ] Exercise an infrastructure failure and confirm it is not recorded as a game loss.
- [ ] Verify token totals reset for each game; missing usage must remain unknown, not zero.

The existing local one-game command is the smoke-test entry point:

```bash
uv run python -m multi_agent_testing.test.debate_test \
  --backend zen \
  --model space-bunny-free \
  --base-url 'https://opencode.ai/zen/v1/' \
  --temperature 0.2 \
  --play \
  --max-rounds 1 \
  --dataset src/data/raw/worldepuzzles.json \
  --puzzle-id 0 \
  --guess-list src/data/raw/allowed_guesses.txt
```

Run this from the user's local repository, not the older Project starter directory. It is not a batch command. The model name records the prototype configuration, not an endorsement of its availability or suitability for final experiments.

Use non-streaming requests initially for experiment verification. Keep the API key in the locally configured environment or ignored `.env`, never in source control or result files.

### Milestone: Freeze the experimental configuration

- [ ] Choose an identifiable model/version for the final study.
- [ ] Record backend, requested/returned model identity when available, temperature, token limits, and timeouts.
- [ ] Freeze personas, decision schema, repair limits, API retry policy, and `max_rounds`.
- [ ] The pilot starts with `max_rounds=3` (recorded 8 October 2026), non-streaming; changing it creates a different configuration.
- [ ] Record code revision, dependency versions, dataset/vocabulary hashes, and prompt versions.
- [ ] Record vocabulary provenance and any mismatch with the human game's historical rules.
- [ ] Keep failed-request usage as unknown when the provider does not report it; do not call the total exact billing usage.

### Milestone: Prepare a puzzle manifest

Create a validated table containing:

```text
puzzle_id, date, answer, human_mean_score, human_label,
human_mode, human_sample_size_if_known, split, eligibility_notes
```

This table is evaluation-only. Select eligible puzzles across the human difficulty range, including both sides of four, using a recorded selection seed.

For an initial pilot, use 20 puzzles and 5 repetitions: 100 planned complete games. This is a development starting point, not a guaranteed sufficient final sample. If pilot results change prompts or settings, keep those puzzles separate from the final evaluation.

If the final set deliberately balances easy/hard classes, state that its class proportions do not represent the full dataset. Freeze the final selection and repetition count after the pilot and before final model runs.

### Milestone: Add a resumable experiment runner

The runner must call the existing game/debate components rather than duplicate their logic:

```text
For each selected puzzle:
    For each planned repetition:
        Create a fresh game and agent/debate state.
        Start a new run log and usage/timing counters.
        Execute one complete game.
        Save completion, failure, or interruption status.
```

- [ ] Start sequentially; avoid concurrent calls until reliability is established.
- [ ] Use unique run IDs and a frozen, reproducible run order.
- [ ] Resume without overwriting or duplicating completed runs.
- [ ] Preserve every failed attempt and its relationship to any replacement run.
- [ ] Predefine bounded retries and replacement policy; never retry until a puzzle wins.
- [ ] Require the planned completed repetitions before including a puzzle in the primary complete-panel analysis.
- [ ] Report omitted puzzles and failures; inspect whether failures concentrate on particular puzzles.

The implemented runner is invoked as `python -m multi_agent_testing.experiment.runner start ...` (or `resume --experiment-dir ...`). It compiles `run_summary.csv` from the run checkpoints, refuses to overwrite completed attempts, and supports bounded execution with `--max-runs`/`--max-seconds` plus exact resume.

### Milestone: Produce analysis-ready outputs

Keep full JSON logs and generate these proposed analysis files:

| File | Purpose |
|---|---|
| `run_summary.csv` | One row per execution attempt, including failed/interrupted attempts. |
| `puzzle_summary.csv` | System mean, standard deviation, win rate, human score, labels, and per-puzzle termination counts. |
| `termination_stats.csv` | Descriptive `gm_stop` vs `max_rounds` mix overall and per easy/hard group (supporting measurement). |
| `metrics.json` | Aggregate RQ1/RQ2 metrics, termination statistics, and analysis settings. |
| `experiment_config.json` | Frozen configuration, versions, thresholds, and selection details. |

Minimum run-summary fields:

```text
run_id, puzzle_id, repetition, attempt, status,
won, guesses_used, penalized_score,
prompt_tokens, completion_tokens, total_tokens,
elapsed_seconds, error_type
```

Reset counters per run. Include all agent calls and corrective attempts when usage is available. Track missing usage and hidden SDK retries explicitly rather than silently undercounting them.

## Analysis and figures

### RQ1 outputs

- Per-puzzle mean and sample standard deviation of penalized guess score.
- Per-puzzle win rate with wins, losses, and completed-run count.
- Distribution of variability across puzzles.
- Variance decomposition across puzzles and repetitions (for example ICC(1,1) and ICC(1,k)), reported alongside within-puzzle SD so the difficulty signal is separated from run-to-run noise.
- Agreement across repetitions: identical triples, pairwise exact matches, and mean pairwise absolute difference.
- An equivalence check against a pre-registered consistency tolerance (within-puzzle SD or agreement level), not a null-hypothesis test of "no difference".
- Separate infrastructure failure and invalid-output rates, including repair-exhaustion counts.

### RQ2 outputs

- Mean absolute error between system and human puzzle means.
- Mean signed error, defined as system mean minus human mean.
- Spearman correlation for relative difficulty; optionally Pearson for linear alignment.
- Confusion matrix, per-class recall, and balanced accuracy for easy/hard agreement.
- Majority-class accuracy as a descriptive reference, not a single-agent baseline.
- Category sensitivity at thresholds 3.8, 4.0, and 4.2.
- Confidence intervals using a documented puzzle-level resampling procedure.

Use one aggregate system score per puzzle for human alignment. Do not count five repetitions of the same puzzle as five independent puzzle observations. Identify puzzles whose uncertainty spans the threshold rather than overstating their labels.

Recommended figures:

- Human mean versus system mean scatter plot with an equality line.
- Per-puzzle variability plot.
- Easy/hard confusion matrix.
- Threshold-sensitivity table or plot.

Report tokens and elapsed time descriptively, including measurement coverage. They do not support claims of comparative efficiency without another architecture.

## Completion criteria and next action

The study is ready for interpretation when the frozen final evaluation has reproducible run logs, validated human-score joins, transparent failure handling, per-puzzle summaries, and RQ1/RQ2 results with uncertainty.

It is not complete merely because a debate returns a valid guess or one puzzle is solved. Conclusions must remain limited to the evaluated model, protocol, puzzle selection, and Wordle rules; correlation alone does not establish exact human-score agreement or causal benefit from debate.

**Immediate next action:** The pilot (`experiments/pilot-01`) has run; its findings and design implications are recorded above. Next: decide the final configuration (review-prompt revision and/or model choice, given the depth-1 finding), strengthen the RQ1 design (hard-tail puzzles, 5 repetitions, ICC plus pre-registered equivalence), then freeze the configuration and run the final evaluation on a fresh puzzle selection. Keep the pilot puzzles out of the final evaluation. Do not add a single-agent mode for this scope.
