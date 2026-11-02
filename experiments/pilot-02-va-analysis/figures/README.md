# Pilot-02 vA figures (P14)

Built by `multi_agent_testing.experiment.plots` from the files in `experiments/pilot-02-va-analysis/` only. Each figure is saved as PDF (vector) and PNG (300 dpi). F1 (human difficulty) is in `experiments/pilot-02/figures/`.

The figures show only axes, panel letters, data values and legends. Every statistic and interpretation is in the caption below. Captions give values only, with p-values for correlations (t-test, n − 2 df). Bootstrap CIs stay in `metrics.json` as a backup.

```bash
uv sync --extra viz
uv run python -m multi_agent_testing.experiment.plots pilot02 \
  --analysis-dir experiments/pilot-02-va-analysis \
  --output-dir experiments/pilot-02-va-analysis/figures
```

## Which figure answers which question

| Question | Figure | Data | What it shows |
|---|---|---|---|
| RQ1 consistency | **F2** Run-to-run spread | deep | Every game of each puzzle |
| RQ2 order (primary) | **F5b** Rank against rank | wide | Spearman ρ and Kendall τ |
| RQ2 order (primary) | **F7** Quartiles by rank | wide | D1–D4 agreement, as points and as counts |
| RQ2 level | **F5a** Mean against mean | wide | Bias on the 6-guess scale |
| RQ2 level | **F6** Bland-Altman | wide | Bias and limits of agreement |
| RQ2 distribution | **F3** 7-bin distributions | deep | Human and system shares per puzzle |
| RQ2 distribution | **F4** W1 by puzzle | deep | Distance per puzzle |
| Persona check | **F8** Persona behaviour | both | Adoption and non-candidate shares |
| Supporting | **F9** Cost and reliability | both | Time, tokens and failed attempts |

Wide (48 puzzles × 3 games) is the RQ2 source. Deep (12 puzzles × 32 games) is the RQ1 and distribution source. vA allows 12 guesses. Agents never see the limit, so a score capped at 7 is the real Wordle score. "Raw" means the 12-guess score, with a loss scored 13.

## Caption drafts

**F2 Run-to-run spread.** Guesses used in each of the 32 games per deep puzzle, under the 12-guess limit. Puzzles are ordered by human mean. Each dot is one game, coloured by human quartile. The black bar is the human mean. The diamond is the system mean. The dashed line marks the real Wordle limit of 6 guesses. HUMOR has 31 games, since one unit failed twice. Within-puzzle SD is 1.53. ICC(1,1) is 0.49.

**F3 Distribution comparison.** Human (grey) and system (blue) shares of games solved in 1 to 6 guesses or failed, for the 12 deep puzzles. System games are read on the 6-guess scale, so any game past guess 6 counts as a fail. W1 is the Wasserstein-1 distance in guesses. Mean W1 is 1.30. The split-half W1 of 0.33 shows that the system's own distribution is stable.

**F4 W1 by puzzle.** Wasserstein-1 distance between the system and human distributions per deep puzzle, on the 6-guess scale. The grey band is the run-to-run noise level (mean W1 between random halves of the same puzzle's runs). Every puzzle lies above it. Mean W1 is 1.30.

**F5 Mean and rank alignment.** Wide puzzles. (a) System mean on the 6-guess scale against the human mean. The system plays 1.28 guesses worse than humans. (b) System rank, from raw 12-guess scores, against human rank. Spearman ρ is 0.34 (p = 0.017). Grey lines mark the D1–D4 boundaries.

**F6 Bland-Altman plot.** Wide puzzles on the 6-guess scale. The bias is +1.28 guesses. The limits of agreement are −0.69 and +3.24. The difference grows with the mean, so the gap is largest on puzzles the system finds hard.

**F7 Quartile confusion.** Wide puzzles, D1–D4 by system rank. (a) Each dot is one puzzle: its system mean on the 12-guess score against its human mean. The dashed lines split the 48 system means into four groups of 12, while the grey lines are the human cut-points. Puzzles that share a system mean on a dashed line are split by puzzle id. (b) The same puzzles as counts and row percentages, with D4 on top so the rows line up with (a). 16 of 48 puzzles agree exactly and 31 lie within one quartile. QWK is 0.27.

**F8 Persona behaviour.** (a) Share of turns where the GM keeps its own proposal or adopts an advisor's suggestion. (b) Share of advisor suggestions from turn 2 on that cannot be the answer. Cautious suggests 13.3 [11.3, 15.5] points more non-candidates than Bold (deep, CI over games), which is the intended direction. Every advisor suggests a non-candidate in most turns.

**F9 Cost and reliability.** (a) Seconds per completed game, with 4 games played in parallel. (b) Prompt and completion tokens per completed game. Both axes stop at the 99th percentile, so 5 games lie beyond each (the slowest took 699 s). (c) Failed attempts by cause. "Runner stopped" marks games abandoned when the runner process ended. Each failed unit was retried once.
