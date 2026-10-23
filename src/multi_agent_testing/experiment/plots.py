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

F1 shows human difficulty and the D1..D4 quartiles. F2-F9 show pilot-02
results and read only an ``analysis_pilot02`` output folder::

    uv run python -m multi_agent_testing.experiment.plots pilot02 \\
        --analysis-dir experiments/pilot-02-va-analysis \\
        --output-dir experiments/pilot-02-va-analysis/figures
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


# ---------------------------------------------------------------------------
# Pilot-02 results (F2-F9), from the analysis outputs only
# ---------------------------------------------------------------------------

# Two-series colours: the system in Okabe-Ito blue, the human reference in a
# neutral grey, so "human" never reads as one more category.
SYSTEM_COLOUR = "#0072B2"
HUMAN_COLOUR = "#9A9A9A"
INK = "#1A1A1A"
MUTED_INK = "#555555"
GRID = "#E6E6E6"
STANDARD_LIMIT = 6  # Wordle guess limit


class Analysis:
    """The files written by ``analysis_pilot02`` for one output folder."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        self.puzzles = self._csv("puzzle_summary.csv")
        self.distribution = self._csv("distribution_summary.csv")
        self.personas = self._csv("persona_stats.csv")
        self.runs = self._csv("runs.csv")

    def _csv(self, name: str) -> list[dict[str, str]]:
        with (self.directory / name).open(encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))

    def block(self, experiment: str) -> dict:
        return self.metrics["experiments"][experiment]

    def puzzle_rows(self, experiment: str) -> list[dict[str, str]]:
        rows = [r for r in self.puzzles if r["experiment"] == experiment and r["system_mean"]]
        return sorted(rows, key=lambda r: (float(r["human_mean"]), int(r["puzzle_id"])))


def _quartile_scatter(ax, xs, ys, quartiles, size: float = 16) -> None:
    for label in QUARTILE_LABELS:
        points = [(x, y) for x, y, q in zip(xs, ys, quartiles) if q == label]
        if points:
            ax.scatter(
                [p[0] for p in points], [p[1] for p in points], s=size,
                color=QUARTILE_COLOURS[label], edgecolor=INK, linewidth=0.4,
                label=label, zorder=3,
            )


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


# Figures carry no titles or notes: panel letters, axes and legends only.
# Numbers and interpretation belong in the caption (figures/README.md).


def _quartile_handles() -> list:
    return [
        plt.Line2D([], [], marker="o", linestyle="", markersize=4.5,
                   markerfacecolor=QUARTILE_COLOURS[q], markeredgecolor=INK,
                   markeredgewidth=0.4)
        for q in QUARTILE_LABELS
    ]


def _line_handle(**style) -> plt.Line2D:
    return plt.Line2D([], [], **style)


DASHED = {"color": MUTED_INK, "linestyle": (0, (3, 2)), "linewidth": 0.7}


def _top_legend(target, handles, labels, ncol: int, **kwargs) -> None:
    """A legend row above the plot, where it cannot cover data."""

    target.legend(handles, labels, loc="lower left", bbox_to_anchor=(0, 1.01), ncol=ncol,
                  frameon=False, handletextpad=0.3, columnspacing=1.0, borderaxespad=0,
                  **kwargs)


def figure_f2(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F2 (RQ1): every deep game's raw score per puzzle, ordered by human mean."""

    block = analysis.block("deep")
    puzzles = analysis.puzzle_rows("deep")
    limit = int(block["max_guesses"])
    scores: dict[str, list[float]] = {}
    for row in analysis.runs:
        if row["experiment"] == "deep" and row["score"]:
            scores.setdefault(row["puzzle_id"], []).append(float(row["score"]))

    _style()
    fig, ax = plt.subplots(figsize=(IEEE_DOUBLE_COLUMN_IN, 2.9))
    ax.axhline(STANDARD_LIMIT + 0.5, zorder=1, **DASHED)

    for x, row in enumerate(puzzles):
        values = sorted(scores.get(row["puzzle_id"], []))
        colour = QUARTILE_COLOURS[row["human_quartile"]]
        # Dot plot: equal scores spread sideways, so every game stays visible.
        for score in sorted(set(values)):
            n = values.count(score)
            step = min(0.06, 0.78 / n)
            offsets = [(k - (n - 1) / 2) * step for k in range(n)]
            ax.scatter([x + o for o in offsets], [score] * n, s=7, color=colour,
                       edgecolor=INK, linewidth=0.25, zorder=3)
        ax.plot([x - 0.42, x + 0.42], [float(row["human_mean"])] * 2, color=INK,
                linewidth=1.4, solid_capstyle="butt", zorder=4)
        ax.scatter([x], [float(row["system_mean"])], marker="D", s=16, color="white",
                   edgecolor=INK, linewidth=0.8, zorder=5)

    ax.set_xticks(range(len(puzzles)))
    ax.set_xticklabels([f"{r['answer']}\n{r['human_quartile']}" for r in puzzles], fontsize=6.5)
    for tick, row in zip(ax.get_xticklabels(), puzzles):
        tick.set_color(QUARTILE_TEXT_COLOURS[row["human_quartile"]])
    ax.set_xlim(-0.6, len(puzzles) - 0.4)
    ax.set_ylim(0.5, limit + 1.5)
    ax.set_yticks(range(1, limit + 2))
    ax.set_yticklabels([str(k) for k in range(1, limit + 1)] + ["Fail"])
    ax.set_ylabel("Guesses used")
    ax.set_xlabel("Deep puzzle (ordered by human mean)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.5, zorder=0)
    _top_legend(
        ax,
        [
            *_quartile_handles(),
            _line_handle(color=INK, linewidth=1.4),
            _line_handle(marker="D", linestyle="", markersize=4, markerfacecolor="white",
                         markeredgecolor=INK),
            _line_handle(**DASHED),
        ],
        [*(f"Game, human {q}" for q in QUARTILE_LABELS), "Human mean", "System mean",
         "6-guess limit"],
        ncol=4,
    )
    return _save(fig, output_dir, "F2_run_to_run_spread")


def figure_f3(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F3 (RQ2 distribution): human and system 7-bin shares per deep puzzle."""

    human_mean = {
        p["puzzle_id"]: float(p["human_mean"]) for p in analysis.puzzles if p["experiment"] == "deep"
    }
    rows = sorted(
        (r for r in analysis.distribution if r["experiment"] == "deep"),
        key=lambda r: human_mean[r["puzzle_id"]],
    )
    columns = 4
    lines = (len(rows) + columns - 1) // columns

    _style()
    fig, axes = plt.subplots(lines, columns, figsize=(IEEE_DOUBLE_COLUMN_IN, 1.32 * lines + 0.3),
                             sharex=True, sharey=True,
                             gridspec_kw={"hspace": 0.55, "wspace": 0.12})
    flat = list(axes.flat)
    bins = range(1, 8)
    for ax, row in zip(flat, rows):
        human = [float(row[f"human_p{k}"]) for k in bins]
        system = [float(row[f"system_p{k}"]) for k in bins]
        ax.bar([k - 0.19 for k in bins], human, width=0.36, color=HUMAN_COLOUR, linewidth=0)
        ax.bar([k + 0.19 for k in bins], system, width=0.36, color=SYSTEM_COLOUR, linewidth=0)
        ax.set_title(f"{row['answer']} ({row['human_quartile']})", loc="left", fontsize=7,
                     color=QUARTILE_TEXT_COLOURS[row["human_quartile"]], fontweight="bold",
                     pad=2)
        ax.yaxis.grid(True, color=GRID, linewidth=0.5)
        ax.set_axisbelow(True)
    for ax in flat[len(rows):]:
        ax.set_visible(False)
    flat[0].set_ylim(0, 1)
    flat[0].set_yticks([0, 0.5, 1])
    flat[0].set_yticklabels(["0", "50", "100"])
    for ax in flat:
        ax.set_xticks(list(bins))
        ax.set_xticklabels(BIN_LABELS, fontsize=6)
    fig.supylabel("Share of games (%)", fontsize=8, x=0.06)
    fig.supxlabel("Guesses", fontsize=8, y=0.03)
    fig.legend([Patch(facecolor=HUMAN_COLOUR), Patch(facecolor=SYSTEM_COLOUR)],
               ["Human", "System"], loc="upper left", ncol=2, frameon=False,
               bbox_to_anchor=(0.115, 1.0), handlelength=1.0)
    return _save(fig, output_dir, "F3_distribution_comparison")


def figure_f4(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F4 (RQ2 distribution): W1 per deep puzzle, by quartile."""

    human_mean = {
        p["puzzle_id"]: float(p["human_mean"]) for p in analysis.puzzles if p["experiment"] == "deep"
    }
    rows = sorted(
        (r for r in analysis.distribution if r["experiment"] == "deep"),
        key=lambda r: human_mean[r["puzzle_id"]],
    )
    summary = analysis.block("deep")["distribution"]

    _style()
    fig, ax = plt.subplots(figsize=(IEEE_SINGLE_COLUMN_IN, 3.0))
    ys = list(range(len(rows)))[::-1]
    noise = "#E8E8E8"
    ax.axvspan(0, summary["mean_split_half_random_w1"], color=noise, zorder=0)
    for y, row in zip(ys, rows):
        colour = QUARTILE_COLOURS[row["human_quartile"]]
        ax.scatter([float(row["w1"])], [y], s=22, color=colour, edgecolor=INK, linewidth=0.4,
                   zorder=3)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['answer']} ({r['human_quartile']})" for r in rows], fontsize=6.5)
    for tick, row in zip(ax.get_yticklabels(), rows):
        tick.set_color(QUARTILE_TEXT_COLOURS[row["human_quartile"]])
    ax.set_xlim(0, None)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlabel("W1 distance to humans (guesses)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)
    _top_legend(
        ax,
        [
            _line_handle(linestyle="", marker="o", markersize=4.5,
                         markerfacecolor="white", markeredgecolor=INK),
            Patch(facecolor=noise),
        ],
        ["W1", "Split-half W1"],
        ncol=2,
    )
    return _save(fig, output_dir, "F4_w1_by_puzzle")


def figure_f5(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F5 (RQ2 mean and rank): wide puzzles on the 6-guess scale and by rank."""

    rows = analysis.puzzle_rows("wide")
    cuts = analysis.metrics["cut_points"]
    human = [float(r["human_mean"]) for r in rows]
    system6 = [float(r["system_mean_6_guesses"]) for r in rows]
    quartiles = [r["human_quartile"] for r in rows]

    _style()
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(IEEE_DOUBLE_COLUMN_IN, 2.9),
                                     gridspec_kw={"wspace": 0.3})

    low, high = 3.4, 7.0
    ax_a.plot([low, high], [low, high], **DASHED)
    for cut in cuts:
        ax_a.axvline(cut, color=GRID, linewidth=0.8, zorder=0)
        ax_a.axhline(cut, color=GRID, linewidth=0.8, zorder=0)
    _quartile_scatter(ax_a, human, system6, quartiles)
    ax_a.set_xlim(low, 5.2)
    ax_a.set_ylim(low, high + 0.15)
    ax_a.set_xlabel("Human mean score")
    ax_a.set_ylabel("System mean score (6 guesses)")
    ax_a.set_title("(a)", loc="left")

    human_rank = _average_ranks(human)
    system_rank = _average_ranks([float(r["system_mean"]) for r in rows])
    n = len(rows)
    ax_b.plot([1, n], [1, n], **DASHED)
    for boundary in (n / 4 + 0.5, n / 2 + 0.5, 3 * n / 4 + 0.5):
        ax_b.axvline(boundary, color=GRID, linewidth=0.8, zorder=0)
        ax_b.axhline(boundary, color=GRID, linewidth=0.8, zorder=0)
    _quartile_scatter(ax_b, human_rank, system_rank, quartiles)
    ax_b.set_xlim(0, n + 1)
    ax_b.set_ylim(0, n + 1)
    ax_b.set_yticks(range(0, n + 1, 10))
    ax_b.set_xlabel("Human rank (1 = easiest)")
    ax_b.set_ylabel("System rank")
    ax_b.set_title("(b)", loc="left")

    fig.legend(
        [*_quartile_handles(), _line_handle(**DASHED), _line_handle(color=GRID, linewidth=1.2)],
        [*(f"Human {q}" for q in QUARTILE_LABELS), "y = x", "D1–D4 boundary"],
        loc="lower left", bbox_to_anchor=(0.11, 0.97), ncol=6, frameon=False,
        handletextpad=0.3, columnspacing=1.0,
    )
    return _save(fig, output_dir, "F5_mean_and_rank_alignment")


def figure_f6(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F6 (RQ2 mean): Bland-Altman plot for wide on the 6-guess scale."""

    rows = analysis.puzzle_rows("wide")
    human = [float(r["human_mean"]) for r in rows]
    system = [float(r["system_mean_6_guesses"]) for r in rows]
    differences = [s - h for s, h in zip(system, human)]
    averages = [(s + h) / 2 for s, h in zip(system, human)]
    bias = sum(differences) / len(differences)
    sd = (sum((d - bias) ** 2 for d in differences) / (len(differences) - 1)) ** 0.5

    _style()
    fig, ax = plt.subplots(figsize=(IEEE_SINGLE_COLUMN_IN, 2.7))
    ax.axhline(0, color=GRID, linewidth=0.8, zorder=0)
    ax.axhline(bias, color=INK, linewidth=0.9)
    for limit in (bias - 1.96 * sd, bias + 1.96 * sd):
        ax.axhline(limit, **DASHED)
    _quartile_scatter(ax, averages, differences, [r["human_quartile"] for r in rows], size=14)
    ax.set_xlim(min(averages) - 0.1, max(averages) + 0.1)
    ax.set_xlabel("Mean of system and human score")
    ax.set_ylabel("System − human (guesses)")
    _top_legend(
        ax,
        [*_quartile_handles(), _line_handle(color=INK, linewidth=0.9), _line_handle(**DASHED)],
        [*(f"Human {q}" for q in QUARTILE_LABELS), "Mean difference", "95% limits of agreement"],
        ncol=3, fontsize=6.5,
    )
    return _save(fig, output_dir, "F6_bland_altman")


def _confusion_panel(ax, matrix: dict, letter: str, system_axis: str) -> None:
    # D4 on top, so the rows line up with a plot whose y axis grows harder.
    counts = matrix["counts"]
    size = len(QUARTILE_LABELS)
    rows = QUARTILE_LABELS[::-1]
    values = [[counts[h][s] for s in QUARTILE_LABELS] for h in rows]
    top = max(max(row) for row in values) or 1
    ax.imshow(values, cmap="Blues", vmin=0, vmax=top * 1.15)
    for i, row in enumerate(values):
        total = sum(row)
        for j, count in enumerate(row):
            share = f"\n{count / total * 100:.0f}%" if total and count else ""
            ax.text(j, i, f"{count}{share}", ha="center", va="center", fontsize=6.5,
                    color="white" if count > top * 0.55 else INK)
    for k in range(size + 1):
        ax.axhline(k - 0.5, color="white", linewidth=1.5)
        ax.axvline(k - 0.5, color="white", linewidth=1.5)
    ax.set_xticks(range(size))
    ax.set_yticks(range(size))
    ax.set_xticklabels(QUARTILE_LABELS)
    ax.set_yticklabels(rows)
    for tick, label in zip(ax.get_yticklabels(), rows):
        tick.set_color(QUARTILE_TEXT_COLOURS[label])
    ax.set_xlabel(system_axis)
    ax.set_ylabel("Human quartile")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(letter, loc="left")


BOUNDARY = "#B5B5B5"  # human D1-D4 lines; GRID is too faint to read as a boundary


def _rank_boundaries(values: list[float], labels: list[str]) -> list[float]:
    """Where the rank split falls between D1..D4 on the value axis.

    Midway between the largest value of one group and the smallest of the
    next. When a value is tied across groups, the boundary sits on it.
    """

    groups = {q: [v for v, label in zip(values, labels) if label == q] for q in QUARTILE_LABELS}
    return [
        (max(groups[low]) + min(groups[high])) / 2
        for low, high in zip(QUARTILE_LABELS, QUARTILE_LABELS[1:])
    ]


def figure_f7(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F7 (RQ2 D1-D4): wide puzzles split by system rank, as points and as counts."""

    rows = analysis.puzzle_rows("wide")
    cuts = analysis.metrics["cut_points"]
    human = [float(r["human_mean"]) for r in rows]
    system = [float(r["system_mean"]) for r in rows]
    quartiles = [r["human_quartile"] for r in rows]
    boundaries = _rank_boundaries(system, [r["system_rank_quartile"] for r in rows])

    _style()
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(IEEE_DOUBLE_COLUMN_IN, 2.8),
                                     gridspec_kw={"wspace": 0.35, "width_ratios": [1.4, 1]})

    x_low, x_high = min(system) - 0.4, max(system) + 0.4
    y_low, y_high = min(human) - 0.08, max(human) + 0.08
    for cut in cuts:
        ax_a.axhline(cut, color=BOUNDARY, linewidth=0.8, zorder=0)
    for boundary in boundaries:
        ax_a.axvline(boundary, zorder=1, **DASHED)
    _quartile_scatter(ax_a, system, human, quartiles)
    ax_a.set_xlim(x_low, x_high)
    ax_a.set_ylim(y_low, y_high)
    ax_a.set_xlabel("System mean score (12 guesses)")
    ax_a.set_ylabel("Human mean score")
    ax_a.set_title("(a)", loc="left", pad=12)
    # Quartile names: system columns along the top, human rows on the right.
    columns = [x_low, *boundaries, x_high]
    for label, left, right in zip(QUARTILE_LABELS, columns, columns[1:]):
        ax_a.text((left + right) / 2, 1.01, label, transform=ax_a.get_xaxis_transform(),
                  ha="center", va="bottom", fontsize=7, color=INK)
    bands = [y_low, *cuts, y_high]
    for label, bottom, top in zip(QUARTILE_LABELS, bands, bands[1:]):
        ax_a.text(1.01, (bottom + top) / 2, label, transform=ax_a.get_yaxis_transform(),
                  ha="left", va="center", fontsize=7, color=QUARTILE_TEXT_COLOURS[label])

    _confusion_panel(ax_b, analysis.block("wide")["rq2"]["rank_confusion_matrix"], "(b)",
                     "System quartile (rank)")

    fig.legend(
        [*_quartile_handles(), _line_handle(**DASHED), _line_handle(color=BOUNDARY, linewidth=1.2)],
        [*(f"Human {q}" for q in QUARTILE_LABELS), "System D1–D4 boundary",
         "Human D1–D4 boundary"],
        loc="lower left", bbox_to_anchor=(0.06, 1.0), ncol=6, frameon=False,
        handletextpad=0.3, columnspacing=1.0,
    )
    return _save(fig, output_dir, "F7_quartile_confusion")


def _paired_bars(ax, groups: list[str], values: dict[str, list[float]], shades: dict) -> None:
    for offset, name in zip((-0.19, 0.19), values):
        bars = ax.bar([k + offset for k in range(len(groups))], values[name], width=0.36,
                      color=shades[name])
        ax.bar_label(bars, labels=[f"{v * 100:.0f}" for v in values[name]], fontsize=6,
                     padding=1.5, color=INK)
    ax.set_xticks(range(len(groups)))
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_yticklabels(["0", "25", "50", "75", "100"])
    ax.yaxis.grid(True, color=GRID, linewidth=0.5)
    ax.set_axisbelow(True)


EXPERIMENT_SHADES = {"deep": SYSTEM_COLOUR, "wide": "#7FB8DA"}


def figure_f8(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F8 (personas): GM retention, advisor adoption and non-candidate shares."""

    rows = {(r["experiment"], r["agent"]): r for r in analysis.personas}
    advisors = [r["agent"] for r in analysis.personas if r["experiment"] == "deep" and r["agent"] != "gm"]

    _style()
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(IEEE_DOUBLE_COLUMN_IN, 2.45),
                                     gridspec_kw={"width_ratios": [1.3, 1.0], "wspace": 0.3})
    groups = ["gm", *advisors]
    _paired_bars(ax_a, groups,
                 {e: [float(rows[(e, g)]["rate"]) for g in groups] for e in EXPERIMENT_SHADES},
                 EXPERIMENT_SHADES)
    ax_a.set_xticklabels(["GM keeps\nown guess", *(f"{a.capitalize()}\nadopted" for a in advisors)],
                         fontsize=6.5)
    ax_a.set_ylabel("Share of turns (%)")
    ax_a.set_title("(a)", loc="left")

    _paired_bars(ax_b, advisors,
                 {e: [float(rows[(e, a)]["non_candidate_share"]) for a in advisors]
                  for e in EXPERIMENT_SHADES},
                 EXPERIMENT_SHADES)
    ax_b.set_xticklabels([a.capitalize() for a in advisors])
    ax_b.set_ylabel("Non-candidate suggestions (%)")
    ax_b.set_title("(b)", loc="left")

    fig.legend([Patch(facecolor=c) for c in EXPERIMENT_SHADES.values()],
               [e.capitalize() for e in EXPERIMENT_SHADES], loc="lower left",
               bbox_to_anchor=(0.11, 0.96), ncol=2, frameon=False, handlelength=1.0)
    return _save(fig, output_dir, "F8_persona_behaviour")


def figure_f9(analysis: Analysis, output_dir: Path) -> list[Path]:
    """F9 (supporting): time and tokens per game, and attempt outcomes."""

    experiments = tuple(EXPERIMENT_SHADES)
    completed = [r for r in analysis.runs if r["status"] == "completed"]

    _style()
    fig, (ax_a, ax_b, ax_c) = plt.subplots(1, 3, figsize=(IEEE_DOUBLE_COLUMN_IN, 2.3),
                                           gridspec_kw={"wspace": 0.38})
    seconds = {e: [float(r["elapsed_seconds"]) for r in completed if r["experiment"] == e]
               for e in experiments}
    tokens = {e: [(int(r["prompt_tokens"]) + int(r["completion_tokens"])) / 1000
                  for r in completed if r["experiment"] == e] for e in experiments}
    for ax, data, label, letter in (
        (ax_a, seconds, "Seconds per game", "(a)"),
        (ax_b, tokens, "Thousand tokens per game", "(b)"),
    ):
        everything = sorted(v for values in data.values() for v in values)
        # The axis stops at the 99th percentile so rare stalls do not flatten
        # the histogram (the caption gives the count beyond it).
        top = everything[int(len(everything) * 0.99)]
        edges = [everything[0] + i * (top - everything[0]) / 24 for i in range(25)]
        ax.hist([[v for v in data[e] if v <= top] for e in experiments], bins=edges,
                stacked=True, color=[EXPERIMENT_SHADES[e] for e in experiments],
                edgecolor="white", linewidth=0.3)
        ax.axvline(everything[len(everything) // 2], color=INK, linewidth=0.8)
        ax.set_xlabel(label)
        ax.set_ylabel("Games")
        ax.set_title(letter, loc="left")

    # A "running" file is a game abandoned when the runner process stopped.
    outcomes = ("RepairExhausted", "APITimeoutError", "running", "other")
    names = {
        "RepairExhausted": "Repair\nexhausted",
        "APITimeoutError": "API\ntimeout",
        "running": "Runner\nstopped",
        "other": "Other",
    }
    counts = {e: {o: 0 for o in outcomes} for e in experiments}
    for row in analysis.runs:
        if row["status"] == "completed":
            continue
        outcome = "running" if row["status"] == "running" else row["error_type"]
        counts[row["experiment"]][outcome if outcome in outcomes else "other"] += 1
    failures = [o for o in outcomes if any(counts[e][o] for e in experiments)]
    for offset, name in zip((-0.19, 0.19), experiments):
        bars = ax_c.bar([k + offset for k in range(len(failures))],
                        [counts[name][o] for o in failures], width=0.36,
                        color=EXPERIMENT_SHADES[name])
        ax_c.bar_label(bars, fontsize=6, padding=1.5, color=INK)
    ax_c.set_xticks(range(len(failures)))
    ax_c.set_xticklabels([names[o] for o in failures], fontsize=6.5)
    ax_c.set_ylabel("Failed attempts")
    ax_c.set_ylim(0, max(max(counts[e].values()) for e in experiments) * 1.2 + 1)
    ax_c.set_title("(c)", loc="left")

    fig.legend([*(Patch(facecolor=c) for c in EXPERIMENT_SHADES.values()),
                _line_handle(color=INK, linewidth=0.8)],
               [*(e.capitalize() for e in experiments), "Median"], loc="lower left",
               bbox_to_anchor=(0.11, 0.97), ncol=3, frameon=False, handlelength=1.2)
    return _save(fig, output_dir, "F9_cost_and_reliability")


PILOT_02_FIGURES = (
    figure_f2, figure_f3, figure_f4, figure_f5, figure_f6, figure_f7, figure_f8, figure_f9,
)


def figures_pilot_02(analysis_dir: Path, output_dir: Path) -> list[Path]:
    analysis = Analysis(analysis_dir)
    return [path for figure in PILOT_02_FIGURES for path in figure(analysis, output_dir)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pilot-02 figures.")
    sub = parser.add_subparsers(dest="figure", required=True)

    f1 = sub.add_parser("f1", help="F1: human difficulty and D1..D4 quartiles.")
    f1.add_argument("--clean-csv", type=Path, required=True)
    f1.add_argument("--quartiles", type=Path, required=True)
    f1.add_argument("--output-dir", type=Path, required=True)

    results = sub.add_parser(
        "pilot02", help="F2-F9: pilot-02 results from an analysis_pilot02 output folder."
    )
    results.add_argument("--analysis-dir", type=Path, required=True)
    results.add_argument("--output-dir", type=Path, required=True)

    args = parser.parse_args()
    if args.figure == "f1":
        paths = figure_f1(args.clean_csv, args.quartiles, args.output_dir)
    else:
        paths = figures_pilot_02(args.analysis_dir, args.output_dir)
    for path in paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
