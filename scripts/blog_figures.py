"""Draw the anth.us article figures (1600x900, plus a 1200x630 preview) into docs/figures/blog/.

    python scripts/blog_figures.py

Same data as scripts/figures.py, in the site's chart style: a large title and subtitle, direct labels, the
categorical blue and orange.
"""
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from figures import INK, INK_2, GRID, KS, SERIES, SURFACE, TASKS, records, stability_rows  # noqa: E402
from decision_averaging.pooled import mean_probabilities, pool, slots  # noqa: E402

OUT = ROOT / "docs" / "figures" / "blog"
NAMES = {"OWA": "true / false / unknown", "CWA": "true / false"}

plt.rcParams.update({"font.size": 13, "axes.titlesize": 13, "axes.labelsize": 13, "legend.fontsize": 13})


def frame(size=(8, 4.5)):
    fig, ax = plt.subplots(figsize=size)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.78, bottom=0.14)
    return fig, ax


def heading(fig, title, subtitle):
    fig.text(0.045, 0.94, title, fontsize=21, fontweight="bold", color=INK, va="top")
    fig.text(0.045, 0.865, subtitle, fontsize=13, color=INK_2, va="top")


def save(fig, name, dpi=200):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=dpi, facecolor=SURFACE)
    plt.close(fig)
    print(f"wrote docs/figures/blog/{name}")


def rows_by_k(task, kind="stability"):
    rows = stability_rows(task)
    if kind == "stability_paired":
        return {int(r["arm"].rsplit("k", 1)[1]): r for r in rows if r["kind"] == kind and r["rule"] == "mean"}
    if kind == "stability_cost":
        return {r["k"]: r for r in rows if r["kind"] == kind}
    return {r["k"]: r for r in rows if r["kind"] == kind and r["rule"] == "mean"}


def flips(name, size=(8, 4.5), dpi=200, preview=False):
    fig, ax = frame(size)
    positions = {k: i for i, k in enumerate(KS)}
    for task, (label, _) in TASKS.items():
        rows = rows_by_k(task)
        x = [positions[k] + (-0.07 if label == "OWA" else 0.07) for k in KS]
        y = [100 * rows[k]["pair_flip_rate"] for k in KS]
        err = [[100 * (rows[k]["pair_flip_rate"] - rows[k]["pair_flip_rate_low"]) for k in KS],
               [100 * (rows[k]["pair_flip_rate_high"] - rows[k]["pair_flip_rate"]) for k in KS]]
        ax.errorbar(x, y, yerr=None if preview else err, color=SERIES[label], lw=3, marker="o", ms=10,
                    elinewidth=1.4, mec=SURFACE, mew=2.5, label=f"{label} ({NAMES[label]})")
    if not preview:
        owa, cwa = rows_by_k("proofwriter-owa", "stability_paired"), rows_by_k("proofwriter-cwa", "stability_paired")
        ax.annotate(f"Ten copies: {100 * owa[10]['flip_reduction']:.0f}% (OWA) and "
                    f"{100 * cwa[10]['flip_reduction']:.0f}% (CWA) fewer changed\n"
                    "answers than one copy, compared on the same problems",
                    xy=(positions[10], 2.4), xytext=(positions[2] + 0.3, 3.3), fontsize=12, color=INK_2,
                    ha="left", va="center", arrowprops={"arrowstyle": "-", "color": INK_2, "lw": 1})
    ax.set_xticks(range(len(KS)), [str(k) for k in KS])
    ax.set_ylim(0, 3.6)
    ax.set_yticks([0, 1, 2, 3], ["0%", "1%", "2%", "3%"])
    ax.set_xlabel("Copies of the question in one request")
    ax.set_ylabel("Repeats that change the answer")
    ax.legend(loc="lower left", handlelength=1.6)
    heading(fig, "How often a repeat changes Jev's answer",
            "Copies pooled in one request, 1,000 logic problems, five runs" +
            ("" if preview else ", 95% intervals"))
    save(fig, name, dpi)


def accuracy():
    fig, ax = frame()
    positions = {k: i for i, k in enumerate(KS)}
    for task, (label, _) in TASKS.items():
        rows = rows_by_k(task)
        y = [100 * rows[k]["accuracy"] for k in KS]
        ax.plot([positions[k] for k in KS], y, color=SERIES[label], lw=3, marker="o", ms=10, mec=SURFACE,
                mew=2.5)
        ax.annotate(f"{label}: {min(y):.1f}% to {max(y):.1f}%", (positions[20], y[-1]), xytext=(-8, 14),
                    textcoords="offset points", ha="right", color=INK_2, fontsize=12)
    ax.set_xticks(range(len(KS)), [str(k) for k in KS])
    ax.set_ylim(70, 100)
    ax.set_yticks([70, 80, 90, 100], ["70%", "80%", "90%", "100%"])
    ax.set_xlabel("Copies of the question in one request")
    ax.set_ylabel("Accuracy")
    heading(fig, "More copies, same accuracy",
            "Share of the 1,000 logic problems answered correctly, averaged over five runs")
    save(fig, "jev-pooled-accuracy.png")


def close_calls():
    task, (_, options) = "proofwriter-owa", TASKS["proofwriter-owa"]
    by_k = {k: records(task, k) for k in (1, 10)}
    base = by_k[1]
    ids = sorted(set.intersection(*(set(rows) for recs in by_k.values() for rows in recs.values())))

    def flip(i):
        a = [slots(base[r][i])[0]["choice"] for r in base]
        return sum(x != y for n, x in enumerate(a) for y in a[n + 1:])

    chosen = sorted(ids, key=lambda i: (-flip(i), i))[:8]
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.5), sharey=True)
    fig.subplots_adjust(left=0.05, right=0.97, top=0.74, bottom=0.14, wspace=0.08)
    for ax, k in zip(axes, (1, 10)):
        for y, i in enumerate(chosen):
            target = Counter(pool(slots(base[r][i]), options, "mean") for r in base).most_common(1)[0][0]
            values = [mean_probabilities(slots(by_k[k][r][i]), options)[target] for r in by_k[k]]
            ax.plot([min(values), max(values)], [y, y], color=GRID, lw=5, solid_capstyle="round", zorder=1)
            ax.scatter(values, [y] * len(values), s=55, color=SERIES["OWA"], zorder=2, lw=1.5, ec=SURFACE)
        ax.set_title("One copy" if k == 1 else "Ten copies", loc="left", fontsize=14)
        ax.set_xlim(0.2, 0.8)
        ax.set_xticks([0.3, 0.5, 0.7], ["0.3", "0.5", "0.7"])
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", left=False, labelleft=False)
    fig.text(0.51, 0.03, "Probability for the item's usual answer, one dot per run", ha="center", color=INK_2)
    heading(fig, "Close calls stay close calls",
            "The eight least stable problems, five runs each. Ten copies pull the runs together.")
    save(fig, "jev-pooled-close-calls.png")


USD_PER_INPUT_TOKEN = 42 / 1e9   # TypeSafe's published Jev price; output tokens are free


def cost():
    fig, ax = frame()
    for task, (label, _) in TASKS.items():
        rows, spend = rows_by_k(task), rows_by_k(task, "stability_cost")
        x = [spend[k]["input_tokens_mean"] * USD_PER_INPUT_TOKEN * 1e6 for k in KS]
        y = [100 * rows[k]["pair_flip_rate"] for k in KS]
        ax.plot(x, y, color=SERIES[label], lw=3, marker="o", ms=10, mec=SURFACE, mew=2.5, label=label)
        if label == "OWA":
            for k, xi, yi in zip(KS, x, y):
                if k == 2:
                    continue
                below = k == 3
                ax.annotate(f"{k} {'copy' if k == 1 else 'copies'}", (xi, yi), xytext=(4 if below else 0,
                            -22 if below else 12), textcoords="offset points", ha="left" if below else "center",
                            color=INK_2, fontsize=11)
    ax.set_xlim(0, 175)
    ax.set_xticks([0, 25, 50, 75, 100, 125, 150, 175], ["$0", "$25", "$50", "$75", "$100", "$125", "$150", "$175"])
    ax.set_ylim(0, 3.0)
    ax.set_yticks([0, 1, 2, 3], ["0%", "1%", "2%", "3%"])
    ax.set_xlabel("Jev cost per million decisions")
    ax.set_ylabel("Repeats that change the answer")
    ax.legend(loc="lower right")
    heading(fig, "What steadier answers cost",
            "At Jev's $42 per billion input tokens; output tokens are free")
    save(fig, "jev-pooled-cost.png")


if __name__ == "__main__":
    flips("jev-pooled-flips.png")
    flips("jev-pooled-preview.png", size=(8, 4.2), dpi=150, preview=True)
    accuracy()
    close_calls()
    cost()
