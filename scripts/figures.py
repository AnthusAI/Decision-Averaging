"""Draw the study 3 figures into docs/figures/ from the committed records (offline, deterministic). The anth.us
article versions come from scripts/blog_figures.py.

    python scripts/figures.py

1. stability-vs-k.png: the chance that a repeated request changes the pooled answer (pair flip rate) against k,
   both tasks, 95% intervals (from studies/*-stability.jsonl).
2. stability-vs-tokens.png: pair flip rate against input tokens per request.
3. copies-within-request.png: every copy's probability for its answer inside one k = 20 request, for stable and
   unstable OWA items.
4. runs-by-k.png: the pooled probability in each of the five runs, for the OWA items that flip most at k = 1,
   at k = 1, 5 and 20.
5. flips-vs-margin.png: per-item flip rate at k = 1 against the item's k = 1 top-two margin.
"""
import gzip
import json
import random
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from decision_averaging.pooled import mean_probabilities, pool, slots  # noqa: E402
from decision_averaging.stability import RUNS  # noqa: E402

OUT = ROOT / "docs" / "figures"
KS = (1, 2, 3, 5, 10, 20)
TASKS = {"proofwriter-owa": ("OWA", ("true", "false", "unknown")), "proofwriter-cwa": ("CWA", ("true", "false"))}
# Reference palette (dataviz skill, light mode): categorical slots 1-2; text and grid inks.
SERIES = {"OWA": "#2a78d6", "CWA": "#eb6834"}
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
})


def records(task, k):
    out = {}
    for run in RUNS:
        path = ROOT / "answers" / f"jev-k{k}" / f"run{run}" / f"{task}.jsonl.gz"
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                out[run] = {r["id"]: r for r in map(json.loads, handle)}
    return out


def stability_rows(task):
    path = ROOT / "studies" / f"{task}-stability.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def flip_rate(answers):
    n = len(answers)
    return sum(a != b for i, a in enumerate(answers) for b in answers[i + 1:]) / (n * (n - 1) / 2)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote docs/figures/{name}")


def stability_vs_k():
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    positions = {k: i for i, k in enumerate(KS)}
    for task, (label, _) in TASKS.items():
        rows = {r["k"]: r for r in stability_rows(task) if r["kind"] == "stability" and r["rule"] == "mean"}
        ks = [k for k in KS if k in rows]
        x = [positions[k] + (-0.06 if label == "OWA" else 0.06) for k in ks]
        y = [100 * rows[k]["pair_flip_rate"] for k in ks]
        err = [[100 * (rows[k]["pair_flip_rate"] - rows[k]["pair_flip_rate_low"]) for k in ks],
               [100 * (rows[k]["pair_flip_rate_high"] - rows[k]["pair_flip_rate"]) for k in ks]]
        ax.errorbar(x, y, yerr=err, color=SERIES[label], lw=2, marker="o", ms=7, capsize=0, elinewidth=1.2,
                    mec=SURFACE, mew=2, label=label)
    ax.set_xticks(range(len(KS)), [str(k) for k in KS])
    ax.set_ylim(bottom=0)
    ax.set_xlabel("copies of the question in one request (k)")
    ax.set_ylabel("repeated requests that change the answer (%)")
    ax.set_title("More copies, fewer changed answers, up to about ten")
    ax.legend(loc="lower left")
    save(fig, "stability-vs-k.png")


def stability_vs_tokens():
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for task, (label, _) in TASKS.items():
        rows = stability_rows(task)
        main = {r["k"]: r for r in rows if r["kind"] == "stability" and r["rule"] == "mean"}
        cost = {r["k"]: r for r in rows if r["kind"] == "stability_cost"}
        ks = [k for k in KS if k in main and k in cost]
        x = [cost[k]["input_tokens_mean"] for k in ks]
        y = [100 * main[k]["pair_flip_rate"] for k in ks]
        ax.plot(x, y, color=SERIES[label], lw=2, marker="o", ms=7, mec=SURFACE, mew=2, label=label)
        for k, xi, yi in zip(ks, x, y):
            if k in (1, 20):
                ax.annotate(f"k = {k}", (xi, yi), xytext=(0, 9), textcoords="offset points", ha="center",
                            color=INK_2, fontsize=9)
    ax.set_xlabel("input tokens per request")
    ax.set_ylabel("run pairs whose answers differ (%)")
    ax.set_ylim(bottom=0)
    ax.set_title("What extra copies buy, per token")
    ax.legend(loc="upper right")
    save(fig, "stability-vs-tokens.png")


def copies_within_request():
    task = "proofwriter-owa"
    first = records(task, 20)[RUNS[0]]
    spread = {}
    for i, row in first.items():
        answers = slots(row)
        top = Counter(a["choice"] for a in answers).most_common(1)[0][0]
        values = [a["probabilities"][top] for a in answers]
        spread[i] = (max(values) - min(values), top, values, len({a["choice"] for a in answers}) > 1)
    split = sorted((i for i in spread if spread[i][3]), key=lambda i: -spread[i][0])[:5]
    steady = sorted((i for i in spread if not spread[i][3]), key=lambda i: spread[i][0])
    calm = [steady[len(steady) * q // 4] for q in (1, 2, 3)]
    chosen = calm + split
    rng = random.Random(0)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for y, i in enumerate(chosen):
        _, top, values, is_split = spread[i]
        jitter = [y + rng.uniform(-0.18, 0.18) for _ in values]
        ax.scatter(values, jitter, s=22, color=SERIES["OWA"] if is_split else INK_2, alpha=0.8, lw=0)
    ax.set_yticks(range(len(chosen)), [f"{'split' if spread[i][3] else 'agreed'}: {i}" for i in chosen], fontsize=8)
    ax.set_xlim(0, 1)
    ax.set_xlabel("each copy's probability for the request's most common answer")
    ax.set_title("Twenty copies in one request, OWA run 3")
    ax.grid(axis="y", visible=False)
    save(fig, "copies-within-request.png")


def runs_by_k():
    task, (_, options) = "proofwriter-owa", TASKS["proofwriter-owa"]
    by_k = {k: records(task, k) for k in (1, 5, 20)}
    base = by_k[1]
    ids = sorted(set.intersection(*(set(rows) for recs in by_k.values() for rows in recs.values())))
    flips = {i: flip_rate([slots(base[r][i])[0]["choice"] for r in base]) for i in ids}
    chosen = sorted(ids, key=lambda i: (-flips[i], i))[:8]
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.8), sharey=True)
    for ax, k in zip(axes, (1, 5, 20)):
        for y, i in enumerate(chosen):
            target = Counter(pool(slots(base[r][i]), options, "mean") for r in base).most_common(1)[0][0]
            values = [mean_probabilities(slots(by_k[k][r][i]), options)[target] for r in by_k[k]]
            ax.plot([min(values), max(values)], [y, y], color=GRID, lw=3, solid_capstyle="round", zorder=1)
            ax.scatter(values, [y] * len(values), s=24, color=SERIES["OWA"], zorder=2, lw=0)
            ax.set_title(f"k = {k}")
        ax.set_xlim(0, 1)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(chosen)), chosen, fontsize=8)
    axes[1].set_xlabel("pooled probability of the item's usual k = 1 answer, one dot per run")
    fig.suptitle("The least stable OWA items, five runs each", x=0.02, y=1.03, ha="left", fontweight="bold",
                 fontsize=11)
    save(fig, "runs-by-k.png")


def flips_vs_margin():
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), sharey=True)
    rng = random.Random(0)
    for ax, (task, (label, _)) in zip(axes, TASKS.items()):
        base = records(task, 1)
        if len(base) < 2:
            ax.set_title(f"{label}, k = 1 (fewer than two runs)")
            continue
        ids = sorted(set.intersection(*(set(rows) for rows in base.values())))
        first = base[RUNS[0]]
        xs, ys = [], []
        for i in ids:
            p = sorted(slots(first[i])[0]["probabilities"].values(), reverse=True)
            xs.append(p[0] - p[1])
            ys.append(flip_rate([slots(base[r][i])[0]["choice"] for r in base]) + rng.uniform(-0.01, 0.01))
        ax.scatter(xs, ys, s=10, color=SERIES[label], alpha=0.35, lw=0)
        ax.axvline(0.15, color=INK_2, lw=1, ls=(0, (3, 3)))
        ax.set_title(f"{label}, k = 1")
        ax.set_xlabel("top-two probability margin (run 3)")
    axes[0].set_ylabel("share of run pairs that disagree")
    save(fig, "flips-vs-margin.png")


if __name__ == "__main__":
    stability_vs_k()
    stability_vs_tokens()
    copies_within_request()
    runs_by_k()
    flips_vs_margin()
