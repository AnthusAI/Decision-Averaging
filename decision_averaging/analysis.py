"""Score every (arm, run, rule) from the committed records. Nothing here calls an engine.

Records live at ``answers/<arm>/run<r>/<task>.jsonl.gz`` where ``<arm>`` is e.g. ``jev-k3``. The
analysis writes ``studies/<task>.jsonl``: one row per result cell, each tagged with ``kind``:

- ``accuracy``: accuracy with a 95% bootstrap interval, overall and (ProofWriter) by proof depth; the
  overall row adds macro-F1, and for ``mean`` the Brier score and ECE (15 bins) of the pooled probabilities.
- ``paired``: accuracy difference against the ``k = 1`` arm on the same items, same run.
- ``retest``: run 1 against run 2 of the same arm and rule (percent agreement, Gwet's AC1, kappa).
- ``slots``: how much the k slots of one request disagree, against how much one slot disagrees with
  itself across the two runs (are slots within a request as independent as separate requests?), and the
  ceiling: the share of items where at least one slot is right.
- ``cost``: input tokens and latency per request.
"""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, List, Optional

from decision_averaging.harness import metrics
from decision_averaging.harness.agreement import bootstrap_ac1, coefficients
from decision_averaging.harness.record import read_by_id
from decision_averaging.harness.scoring import _sort_key, write_rows
from decision_averaging.harness.tasks import Task

from decision_averaging.pooled import ARM, RULES, arm_k, mean_probabilities, pool, slots

ROOT = Path(__file__).resolve().parents[1]
KINDS = ("k", "perm", "para")
STUDY_RUNS = (1, 2)   # studies 1 and 2; study 3's runs 3-7 are scored by ``stability``
ECE_BINS = 15


def record_path(arm: str, run: int, task: str, *, root: Path = ROOT) -> Path:
    return Path(root) / "answers" / arm / f"run{run}" / f"{task}.jsonl.gz"


def arms(task: str, *, root: Path = ROOT) -> Dict[str, Dict[int, Path]]:
    found: Dict[str, Dict[int, Path]] = {}
    for path in sorted((Path(root) / "answers").glob(f"*/run*/{task}.jsonl.gz")):
        found.setdefault(path.parent.parent.name, {})[int(path.parent.name[3:])] = path
    found = {arm: runs for arm, runs in found.items() if ARM.match(arm)}
    return dict(sorted(found.items(), key=lambda kv: arm_order(kv[0])))


def arm_order(arm: str):
    m = ARM.match(arm)
    return (m["engine"], KINDS.index(m["kind"]), int(m["k"]))


def _k(arm: str) -> int:
    return arm_k(arm)


def brier_and_ece(probabilities: List[Dict[str, float]], gold: List[str], options) -> tuple:
    """Multiclass Brier score (sum over options) and top-label ECE with equal-width bins."""
    brier = metrics.mean([sum((p[o] - (o == g)) ** 2 for o in options) for p, g in zip(probabilities, gold)])
    bins: Dict[int, List[tuple]] = {}
    for p, g in zip(probabilities, gold):
        top = max(options, key=lambda o: p[o])
        bins.setdefault(min(int(p[top] * ECE_BINS), ECE_BINS - 1), []).append((p[top], int(top == g)))
    ece = sum(len(b) * abs(metrics.mean([c for c, _ in b]) - metrics.mean([h for _, h in b]))
              for b in bins.values()) / len(gold)
    return brier, ece


def _quantile(values: List[float], q: float) -> Optional[float]:
    values = sorted(values)
    return values[int(q * (len(values) - 1))] if values else None


def analyse(task: Task, *, root: Path = ROOT) -> List[dict]:
    items = {i["id"]: i for i in task.load_items()}
    found = {arm: {r: p for r, p in runs.items() if r in STUDY_RUNS}
             for arm, runs in arms(task.slug, root=root).items()}
    found = {arm: runs for arm, runs in found.items() if runs}
    records = {(arm, run): read_by_id(path) for arm, runs in found.items() for run, path in runs.items()}
    out: List[dict] = []
    axes = ("overall", "depth") if all("depth" in i["metadata"] for i in items.values()) else ("overall",)

    def choices(arm: str, run: int, rule: str) -> Dict[str, Optional[str]]:
        return {i: pool(slots(row), task.options, rule) for i, row in records[(arm, run)].items() if i in items}

    for (arm, run), rows in records.items():
        for rule in RULES:
            picked = choices(arm, run, rule)
            for axis in axes:
                groups: Dict[str, List[str]] = {}
                for i in picked:
                    value = "all" if axis == "overall" else str(items[i]["metadata"]["depth"])
                    groups.setdefault(value, []).append(i)
                for value in sorted(groups, key=_sort_key):
                    correct = [int(picked[i] == items[i]["metadata"]["reference_label"]) for i in groups[value]]
                    low, high = metrics.bootstrap_ci(correct)
                    cell = {"kind": "accuracy", "task": task.slug, "arm": arm, "k": _k(arm), "run": run,
                            "rule": rule, "axis": axis, "value": value, "n": len(correct),
                            "accuracy": metrics.mean(correct), "ci_low": low, "ci_high": high,
                            "invalid": sum(picked[i] is None for i in groups[value])}
                    if axis == "overall":
                        ids = groups[value]
                        gold = [items[i]["metadata"]["reference_label"] for i in ids]
                        cell["macro_f1"] = metrics.macro_f1(metrics.confusion(
                            gold, [picked[i] or "" for i in ids], task.options))
                        probs = [mean_probabilities(slots(rows[i]), task.options) for i in ids]
                        if rule == "mean" and all(probs):
                            cell["brier"], cell["ece"] = brier_and_ece(probs, gold, task.options)
                    out.append(cell)
            base = f"{ARM.match(arm)['engine']}-k1"
            if _k(arm) > 1 and (base, run) in records:
                reference = choices(base, run, rule)
                common = [i for i in picked if i in reference]
                for axis in axes:
                    values = ["all"] if axis == "overall" else sorted(
                        {str(items[i]["metadata"]["depth"]) for i in common}, key=_sort_key)
                    for value in values:
                        ids = [i for i in common if axis == "overall" or str(items[i]["metadata"]["depth"]) == value]
                        gold = [items[i]["metadata"]["reference_label"] for i in ids]
                        diff, low, high = metrics.paired_diff_ci([int(picked[i] == g) for i, g in zip(ids, gold)],
                                                                 [int(reference[i] == g) for i, g in zip(ids, gold)])
                        out.append({"kind": "paired", "task": task.slug, "arm": arm, "versus": base, "run": run,
                                    "rule": rule, "axis": axis, "value": value, "n": len(ids),
                                    "diff": diff, "ci_low": low, "ci_high": high})
        usage = [r.get("usage") or {} for r in rows.values()]
        latency = [r["latency_ms"] for r in rows.values() if r.get("latency_ms") is not None]
        tokens = [u["input_tokens"] for u in usage if u.get("input_tokens")]
        out.append({"kind": "cost", "task": task.slug, "arm": arm, "k": _k(arm), "run": run, "n": len(rows),
                    "input_tokens_mean": sum(tokens) / len(tokens) if tokens else None,
                    "latency_p50": _quantile(latency, 0.5), "latency_p90": _quantile(latency, 0.9)})

    for arm, runs in found.items():
        if 1 in runs and 2 in runs:
            for rule in RULES:
                first, second = choices(arm, 1, rule), choices(arm, 2, rule)
                pairs = [(first[i], second[i]) for i in first if i in second]
                if pairs:
                    row = {"kind": "retest", "task": task.slug, "arm": arm, "k": _k(arm), "rule": rule,
                           "n": len(pairs), **coefficients(pairs, task.options),
                           "changed": sum(a != b for a, b in pairs)}
                    row["ac1_low"], row["ac1_high"] = bootstrap_ac1(pairs, task.options)
                    out.append(row)
        if _k(arm) > 1:
            for run in sorted(runs):
                rows = records[(arm, run)]
                within = [int(a.get("choice") != b.get("choice"))
                          for row in rows.values() for a, b in itertools.combinations(slots(row), 2)]
                split = [int(len({s.get("choice") for s in slots(row)}) > 1) for row in rows.values()]
                spread = [max(s["probabilities"][o] for s in slots(row)) - min(s["probabilities"][o] for s in slots(row))
                          for row in rows.values() if all(s.get("probabilities") for s in slots(row))
                          for o in task.options]
                ceiling = [int(any(s.get("choice") == items[i]["metadata"]["reference_label"] for s in slots(row)))
                           for i, row in rows.items() if i in items]
                out.append({"kind": "slots", "task": task.slug, "arm": arm, "k": _k(arm), "run": run,
                            "n": len(rows), "pairwise_disagreement": metrics.mean(within) if within else None,
                            "any_slot_right": metrics.mean(ceiling) if ceiling else None,
                            "split_requests": metrics.mean(split) if split else None,
                            "mean_probability_range": metrics.mean(spread) if spread else None})
            if 1 in runs and 2 in runs:
                a, b = records[(arm, 1)], records[(arm, 2)]
                across = [int(sa.get("choice") != sb.get("choice"))
                          for i in a if i in b for sa, sb in zip(slots(a[i]), slots(b[i]))]
                out.append({"kind": "slots", "task": task.slug, "arm": arm, "k": _k(arm), "run": "1-vs-2",
                            "n": len(across), "same_slot_disagreement_across_runs": metrics.mean(across)})
    return out


def replay(task: Task, *, root: Path = ROOT) -> Optional[Path]:
    rows = analyse(task, root=root)
    if not rows:
        return None
    path = Path(root) / "studies" / f"{task.slug}.jsonl"
    write_rows(path, rows)
    return path
