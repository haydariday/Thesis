"""Figures for pilot-02 (Section 8 of docs/experiments/pilot-02-plan.md).

Figures are built only from processed files (the cleaned human CSV,
``quartiles.json`` and, later, analysis outputs), never from raw run logs, so
every figure matches the reported numbers. Requires the optional ``viz``
extra::

    uv sync --extra viz
    uv run python -m multi_agent_testing.experiment.plots f1 \\
        --clean-csv src/data/processed/wordle_human_clean.csv \\
        --quartiles src/data/processed/quartiles.json \\
        --output-dir experiments/pilot-02/figures

Each figure is written as PDF (vector, for the paper) and PNG (300 dpi, for
slides and notes) at IEEE column widths.

Implemented so far: F1 (human difficulty and the D1..D4 quartiles).
"""

import argparse
import csv
import json
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
except ModuleNotFoundError as error:  # pragma: no cover - exercised manually
    raise SystemExit(
        "matplotlib is missing. Install the optional extra: uv sync --extra viz"
    ) from error

from .quartiles import QUARTILE_LABELS

IEEE_SINGLE_COLUMN_IN = 3.5
IEEE_DOUBLE_COLUMN_IN = 7.16

# Okabe-Ito, colourblind-safe. One colour per difficulty quartile.
QUARTILE_COLOURS = {
    "D1": "#56B4E9",  # sky blue
    "D2": "#009E73",  # bluish green
    "D3": "#E69F00",  # orange
    "D4": "#D55E00",  # vermillion
}
# Darker text variants of the same hues, for labels on white (WCAG >= 4.5:1).
QUARTILE_TEXT_COLOURS = {
    "D1": "#0B5F8F",
    "D2": "#00674B",
    "D3": "#8A5A00",
    "D4": "#A63F00",
}
# Guess-count bins: light-to-dark blue for solves, a dark neutral for fail so
# it never reads as "one more guess".
BIN_COLOURS = ("#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c", "#3a3a3a")
BIN_LABELS = ("1", "2", "3", "4", "5", "6", "Fail")


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 8.5,
            "axes.labelsize": 8,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "pdf.fonttype": 42,  # embed TrueType so IEEE PDF checks pass
            "ps.fonttype": 42,
            "savefig.dpi": 300,
        }
    )


def _save(fig, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for suffix in ("pdf", "png"):
        path = output_dir / f"{stem}.{suffix}"
        # Fixed metadata keeps the PDF byte-stable between rebuilds.
        metadata = {"CreationDate": None} if suffix == "pdf" else {"Software": None}
        fig.savefig(path, bbox_inches="tight", pad_inches=0.02, metadata=metadata)
        paths.append(path)
    plt.close(fig)
    return paths


def _load_eligible(clean_csv: Path) -> list[dict[str, str]]:
    with clean_csv.open(encoding="utf-8", newline="") as file:
        return [row for row in csv.DictReader(file) if row["eligible"] == "True"]


def figure_f1(clean_csv: Path, quartiles_json: Path, output_dir: Path) -> list[Path]:
    """F1: human mean-score histogram with D1..D4 bands, and the mean 7-bin
    distribution of each quartile as stacked bars."""

    rows = _load_eligible(clean_csv)
    spec = json.loads(quartiles_json.read_text(encoding="utf-8"))
    cuts: list[float] = spec["cut_points"]
    ranges = spec["ranges"]
    descriptives = spec["descriptives"]

    _style()
    fig, (ax_hist, ax_bins) = plt.subplots(
        1, 2, figsize=(IEEE_DOUBLE_COLUMN_IN, 2.55),
        gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.32},
    )

    # (a) Histogram, one colour per quartile (puzzles keep their rank label, so
    # tied boundary values are split exactly as in quartiles.json).
    # Bin edges are aligned to the cut-points so no bar straddles a boundary;
    # inside each quartile the width is the nearest fit to 0.05.
    low = 3.25
    high = 6.25
    edges: list[float] = []
    for lo, hi in zip([low, *cuts], [*cuts, high]):
        count = max(1, round((hi - lo) / 0.05))
        step = (hi - lo) / count
        edges.extend(lo + i * step for i in range(count))
    edges.append(high)
    stacks = []
    for label in QUARTILE_LABELS:
        stacks.append([float(r["human_mean_score"]) for r in rows if r["quartile"] == label])
    ax_hist.hist(
        stacks, bins=edges, stacked=True,
        color=[QUARTILE_COLOURS[q] for q in QUARTILE_LABELS],
        edgecolor="white", linewidth=0.3, label=list(QUARTILE_LABELS),
    )
    ymax = ax_hist.get_ylim()[1] * 1.22
    ax_hist.set_ylim(0, ymax)
    for cut in cuts:
        ax_hist.axvline(cut, ymax=0.97, color="#333333", linestyle=(0, (3, 2)), linewidth=0.7)
        # Cut values sit just above the axes, clear of bars and labels.
        ax_hist.text(cut, ymax * 1.005, f"{cut:.2f}", ha="center", va="bottom", fontsize=6.5,
                     color="#333333", clip_on=False)
    centres = [
        (ranges["D1"]["min"] + cuts[0]) / 2,
        (cuts[0] + cuts[1]) / 2,
        (cuts[1] + cuts[2]) / 2,
        (cuts[2] + 5.0) / 2,
    ]
    for label, x in zip(QUARTILE_LABELS, centres):
        ax_hist.text(x, ymax * 0.9, label, ha="center", va="center", fontsize=8,
                     fontweight="bold", color=QUARTILE_TEXT_COLOURS[label])
    ax_hist.set_xlim(low, high)
    ax_hist.set_xlabel("Human mean guess score (fail = 7)")
    ax_hist.set_ylabel("Puzzles per bin (width \u2248 0.05)")
    ax_hist.set_title(f"(a) Human difficulty, n = {spec['population_size']:,}", loc="left", pad=11)

    # (b) Mean 7-bin distribution per quartile.
    y_positions = list(range(len(QUARTILE_LABELS)))[::-1]  # D1 on top
    for y, label in zip(y_positions, QUARTILE_LABELS):
        shares = [descriptives[label]["mean_bins"][f"p{k}"] for k in range(1, 8)]
        left = 0.0
        for k, share in enumerate(shares):
            ax_bins.barh(y, share, left=left, height=0.68, color=BIN_COLOURS[k],
                         edgecolor="white", linewidth=0.4)
            if share >= 0.07:
                text_colour = "white" if k >= 4 else "#1a1a1a"
                ax_bins.text(left + share / 2, y, f"{share * 100:.0f}", ha="center",
                             va="center", fontsize=6.5, color=text_colour)
            left += share
    ax_bins.set_yticks(y_positions)
    ax_bins.set_yticklabels(
        [f"{q}\n{ranges[q]['min']:.2f}\u2013{ranges[q]['max']:.2f}" for q in QUARTILE_LABELS],
        fontsize=7,
    )
    for tick, label in zip(ax_bins.get_yticklabels(), QUARTILE_LABELS):
        tick.set_color(QUARTILE_TEXT_COLOURS[label])
        tick.set_fontweight("bold")
    ax_bins.set_xlim(0, 1)
    ax_bins.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax_bins.set_xticklabels(["0", "25", "50", "75", "100"])
    ax_bins.set_xlabel("Share of human games (%)")
    ax_bins.set_title("(b) Mean guess-count distribution", loc="left", pad=11)
    ax_bins.spines["left"].set_visible(False)
    ax_bins.tick_params(axis="y", length=0)
    handles = [Patch(facecolor=c, edgecolor="#999999", linewidth=0.3) for c in BIN_COLOURS]
    ax_bins.legend(
        handles, BIN_LABELS, title="Guesses", title_fontsize=7, ncol=7,
        loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False,
        handlelength=1.0, handletextpad=0.3, columnspacing=0.7,
    )

    return _save(fig, output_dir, "F1_human_difficulty")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pilot-02 figures.")
    sub = parser.add_subparsers(dest="figure", required=True)

    f1 = sub.add_parser("f1", help="F1: human difficulty and D1..D4 quartiles.")
    f1.add_argument("--clean-csv", type=Path, required=True)
    f1.add_argument("--quartiles", type=Path, required=True)
    f1.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.figure == "f1":
        for path in figure_f1(args.clean_csv, args.quartiles, args.output_dir):
            print(f"Wrote {path}")


if __name__ == "__main__":
    main()
