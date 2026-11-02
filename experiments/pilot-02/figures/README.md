# Pilot-02 figures

Built by `multi_agent_testing.experiment.plots` from processed files only. Each figure is saved as PDF (vector) and PNG (300 dpi).

## F1 Human difficulty and D1–D4 quartiles

`F1_human_difficulty.{pdf,png}` (P2). Rebuild:

```bash
uv sync --extra viz
uv run python -m multi_agent_testing.experiment.plots f1 \
  --clean-csv src/data/processed/wordle_human_clean.csv \
  --quartiles src/data/processed/quartiles.json \
  --output-dir experiments/pilot-02/figures
```

Caption draft: (a) Distribution of human mean guess scores (fail scored as 7) for the 1,861 eligible standard-mode puzzles, coloured by difficulty quartile. Dashed lines mark the cut-points 3.98, 4.24 and 4.53. Bin edges are aligned to the cut-points. The small lower-quartile slivers at the start of the 3.98, 4.24 and 4.53 bars are the 3, 13 and 1 puzzles that tie with the cut value and are assigned to the lower quartile by rank. (b) Mean share of human games ending in 1–6 guesses or a fail, by quartile. Labels show percentages of 7% or more.
