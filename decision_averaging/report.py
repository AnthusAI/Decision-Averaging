"""Regenerate RESULTS.md from ``studies/*.jsonl`` (never from a live engine)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from decision_averaging.analysis import ROOT, arm_order

TASKS = ("proofwriter-owa", "proofwriter-cwa", "emotion")


def _pct(x) -> str:
    return "-" if x is None else f"{100 * x:.1f}"


def _signed(x) -> str:
    return f"{100 * x:+.1f}"


def task_section(slug: str, rows: List[dict]) -> List[str]:
    lines = [f"## {slug}", ""]
    acc = [r for r in rows if r["kind"] == "accuracy"]
    if not acc:
        return lines + ["No arm has been answered on this task yet.", ""]
    arms = sorted({r["arm"] for r in acc}, key=arm_order)
    runs = sorted({r["run"] for r in acc})
    lines += ["### Accuracy (95% bootstrap interval)", "",
              "| arm | rule | " + " | ".join(f"run {r}" for r in runs) + " |", "|---|---|" + "---|" * len(runs)]
    for arm in arms:
        for rule in ("vote", "mean") if not arm.endswith("-k1") else ("vote",):
            cells = []
            for run in runs:
                m = next((r for r in acc if r["arm"] == arm and r["rule"] == rule and r["run"] == run
                          and r["axis"] == "overall"), None)
                cells.append("-" if m is None else f"{_pct(m['accuracy'])} [{_pct(m['ci_low'])}-{_pct(m['ci_high'])}]")
            lines.append(f"| {arm} | {'-' if arm.endswith('-k1') else rule} | " + " | ".join(cells) + " |")
    scored = [r for r in acc if r["axis"] == "overall" and r["rule"] == "mean"]
    lines += ["", "### Macro-F1 and probability scores (`mean` rule; Brier summed over options, ECE 15 bins)", "",
              "| arm | run | macro-F1 | Brier | ECE |", "|---|---|---|---|---|"]
    for r in scored:
        lines.append(f"| {r['arm']} | {r['run']} | {r['macro_f1']:.3f} | "
                     f"{'-' if r.get('brier') is None else format(r['brier'], '.3f')} | "
                     f"{'-' if r.get('ece') is None else format(r['ece'], '.3f')} |")
    depths = sorted({r["value"] for r in acc if r["axis"] == "depth"}, key=int)
    if depths:
        lines += ["", "### Accuracy by proof depth (run 1; `vote` for k > 1, the `mean` rule is in the studies file)", "",
                  "| depth | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
        for d in depths:
            cells = []
            for arm in arms:
                m = next((r for r in acc if r["arm"] == arm and r["rule"] == "vote" and r["run"] == 1
                          and r["axis"] == "depth" and r["value"] == d), None)
                cells.append("-" if m is None else _pct(m["accuracy"]))
            lines.append(f"| {d} | " + " | ".join(cells) + " |")
    paired = [r for r in rows if r["kind"] == "paired" and r["axis"] == "overall"]
    if paired:
        lines += ["", "### Against one copy (same items, same run; accuracy difference in points)", "",
                  "| arm | rule | run | difference | 95% interval |", "|---|---|---|---|---|"]
        for r in paired:
            lines.append(f"| {r['arm']} | {r['rule']} | {r['run']} | {_signed(r['diff'])} | "
                         f"{_signed(r['ci_low'])} to {_signed(r['ci_high'])} |")
    retest = [r for r in rows if r["kind"] == "retest"]
    if retest:
        lines += ["", "### Test-retest (run 1 against run 2)", "",
                  "| arm | rule | agreement | AC1 | kappa | changed |", "|---|---|---|---|---|---|"]
        for r in retest:
            lines.append(f"| {r['arm']} | {r['rule']} | {_pct(r['agreement'])} | {r['ac1']:.3f} "
                         f"[{r['ac1_low']:.3f}-{r['ac1_high']:.3f}] | {r['kappa']:.3f} | {r['changed']} |")
    slot_rows = [r for r in rows if r["kind"] == "slots"]
    if slot_rows:
        lines += ["", "### Slots within one request", "",
                  "Pairwise disagreement: share of slot pairs in one request with different answers. Across runs: "
                  "share of slots whose answer differs between run 1 and run 2 (separate requests).", "",
                  "| arm | run | pairwise disagreement | requests with a split vote | mean probability range | "
                  "any slot right | same slot across runs |", "|---|---|---|---|---|---|---|"]
        for r in slot_rows:
            lines.append(f"| {r['arm']} | {r['run']} | {_pct(r.get('pairwise_disagreement'))} | "
                         f"{_pct(r.get('split_requests'))} | {_pct(r.get('mean_probability_range'))} | "
                         f"{_pct(r.get('any_slot_right'))} | "
                         f"{_pct(r.get('same_slot_disagreement_across_runs'))} |")
    cost = [r for r in rows if r["kind"] == "cost"]
    if cost:
        lines += ["", "### Cost and latency per request", "",
                  "| arm | run | input tokens | p50 ms | p90 ms |", "|---|---|---|---|---|"]
        for r in cost:
            lines.append(f"| {r['arm']} | {r['run']} | {r['input_tokens_mean']:.0f} | {r['latency_p50']:.0f} | "
                         f"{r['latency_p90']:.0f} |")
    return lines + [""]


def render(*, root: Path = ROOT) -> str:
    lines = ["# Results", "", "Generated by `da report` from `studies/*.jsonl`; do not edit by hand.", ""]
    for slug in TASKS:
        path = Path(root) / "studies" / f"{slug}.jsonl"
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []
        lines += task_section(slug, rows)
    return "\n".join(lines).rstrip() + "\n"


def write(*, root: Path = ROOT) -> Path:
    path = Path(root) / "RESULTS.md"
    path.write_text(render(root=root), encoding="utf-8")
    return path
