"""Power simulation behind the final-study size (docs/experiments/final-plan.md, Section 5).

Draws stratified puzzles from the real human means, generates whole-number guess counts with the pilot's
configuration-vB noise (within SD about 0.6 before rounding, bias -0.55) and reports, per design, the power of
Spearman's rho against zero and the 95% range of rho, ICC(1,1), MAE and the rank-quartile exact rate.

Needs numpy and scipy, which are not project dependencies:
    uv run --with numpy --with scipy python docs/experiments/final-power-sim.py \
        src/data/processed/wordle_human_clean.csv check   # reproduce the pilot sizes (48x3, 12x32)
    uv run --with numpy --with scipy python docs/experiments/final-power-sim.py \
        src/data/processed/wordle_human_clean.csv run     # candidate designs
"""
import csv, sys
import numpy as np
from scipy import stats

rng = np.random.default_rng(20261102)
H = [(float(r["human_mean_score"]), r["quartile"]) for r in csv.DictReader(open(sys.argv[1])) if r["eligible"] == "True"]
byq = {q: np.array([h for h, qq in H if qq == q]) for q in ("D1", "D2", "D3", "D4")}
cuts = [3.98, 4.24, 4.53]

def icc11(x):
    n, k = x.shape
    gm = x.mean()
    msb = k * ((x.mean(1) - gm) ** 2).sum() / (n - 1)
    msw = ((x - x.mean(1, keepdims=True)) ** 2).sum() / (n * (k - 1))
    return (msb - msw) / (msb + (k - 1) * msw)

def sim(n, k, rho, sigma_b, sigma_w=0.60, bias=-0.55, reps=2000):
    out = {"rho": [], "p": [], "icc": [], "mae": [], "rqx": []}
    for _ in range(reps):
        h = np.concatenate([rng.choice(byq[q], n // 4, replace=False) for q in byq])
        hz = (h - h.mean()) / h.std()
        true = h.mean() + bias + sigma_b * (rho * hz + np.sqrt(1 - rho ** 2) * rng.standard_normal(n))
        runs = np.clip(np.rint(true[:, None] + sigma_w * rng.standard_normal((n, k))), 1, 7)
        m = runs.mean(1)
        r, p = stats.spearmanr(m, h)
        out["rho"].append(r); out["p"].append(p); out["icc"].append(icc11(runs))
        out["mae"].append(np.abs(m - h).mean())
        hq = np.digitize(h, cuts); sq = np.digitize(stats.rankdata(m, method="ordinal"), np.quantile(np.arange(1, n + 1), [.25, .5, .75]))
        out["rqx"].append((hq == sq).mean())
    o = {k: np.array(v) for k, v in out.items()}
    q = lambda a: f"{np.median(a):.2f} [{np.quantile(a, .025):.2f}, {np.quantile(a, .975):.2f}]"
    return f"power {np.mean(o['p'] < .05):.0%} | rho {q(o['rho'])} | ICC11 {q(o['icc'])} | MAE {q(o['mae'])} | rankQ exact {q(o['rqx'])}"

if sys.argv[2] == "check":
    # Does the model reproduce the pilot? (vB wide 48x3: rho .28, ICC .25; vB deep 12x32: rho .66, ICC .44)
    for sb in (0.35, 0.5):
        for rho in (0.4, 0.5, 0.6):
            print(f"sb={sb} rho={rho}  48x3:", sim(48, 3, rho, sb, reps=1000))
            print(f"               12x32:", sim(12, 32, rho, sb, reps=1000))
else:
    for sb in (0.35, 0.5):
        for rho in (0.4, 0.5, 0.6):
            print(f"\n== sigma_b={sb}, true rho={rho}")
            for n, k in ((60, 10), (100, 10), (60, 20), (60, 32), (100, 5)):
                print(f"  {n:>3} x {k:<2}", sim(n, k, rho, sb))
