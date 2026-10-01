"""Study 3: how repeatable is the pooled answer as k grows? Nothing here calls an engine.

Each arm ``jev-k<k>`` is answered in runs 3-7 (``docs/preregistration-3.md``) on the 1,000 items per task
listed in ``tasks/<task>/stability-ids.txt``. Treating each run as a rater,
this scores, per arm and pooling rule:

- ``agreement`` and ``ac1``: Gwet's multi-rater percent agreement and AC1 across all runs (Gwet 2008), with a
  95% percentile bootstrap interval over items (seed 0, 1,000 resamples).
- ``changed``: items whose pooled answer is not the same in every run; ``pair_flip_rate``: the share of run
  pairs that disagree, averaged over items.
- ``probability_sd``: per item, the standard deviation across runs of the pooled probability of the item's
  most common answer, averaged over items.
- accuracy (mean over runs), input tokens and latency per request.

``paired`` rows give each arm's AC1 minus ``jev-k1``'s on the same bootstrap resamples of the same items.
Rows go to ``studies/<task>-stability.jsonl``.
"""
from __future__ import annotations

import itertools
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from decision_averaging.analysis import ROOT, arm_order, arms
from decision_averaging.harness.record import read_by_id
from decision_averaging.harness.scoring import write_rows
from decision_averaging.harness.tasks import Task
from decision_averaging.pooled import RULES, arm_k, mean_probabilities, pool, slots

RUNS = (3, 4, 5, 6, 7)
IDS_FILE = "stability-ids.txt"   # the 1,000 items per task this study answers (scripts/draw_stability_items.py)
RESAMPLES, SEED = 1000, 0
NEAR_TIE = 0.15


def multi_rater(ratings: Sequence[Sequence[Optional[str]]], categories: Sequence[str]) -> Dict[str, float]:
    """Gwet's multi-rater percent agreement and AC1. ``ratings`` holds one list of labels per item, one label
    per rater (run). An invalid answer (None) is its own category."""
    cats = list(categories) + ([None] if any(r is None for item in ratings for r in item) else [])
    agree, shares = [], Counter()
    for item in ratings:
        n = len(item)
        counts = Counter(item)
        agree.append(sum(c * (c - 1) for c in counts.values()) / (n * (n - 1)))
        for c, v in counts.items():
            shares[c] += v / n
    observed = sum(agree) / len(agree)
    chance = sum((shares[c] / len(ratings)) * (1 - shares[c] / len(ratings)) for c in cats) / (len(cats) - 1)
    return {"agreement": observed, "ac1": 1.0 if chance >= 1 else (observed - chance) / (1 - chance)}


def _resamples(n: int) -> List[List[int]]:
    rng = random.Random(SEED)
    return [[rng.randrange(n) for _ in range(n)] for _ in range(RESAMPLES)]


def _interval(values: List[float]) -> tuple:
    values = sorted(values)
    return values[int(0.025 * len(values))], values[min(len(values) - 1, int(0.975 * len(values)))]


def _margin(row: dict) -> Optional[float]:
    probabilities = slots(row)[0].get("probabilities")
    if not probabilities:
        return None
    top = sorted(probabilities.values(), reverse=True)
    return top[0] - top[1]


def study_ids(task: Task) -> Optional[set]:
    path = task.dir / IDS_FILE
    return set(path.read_text(encoding="utf-8").split()) if path.exists() else None


def analyse(task: Task, *, root: Path = ROOT) -> List[dict]:
    chosen = study_ids(task)
    items = {i["id"]: i for i in task.load_items() if chosen is None or i["id"] in chosen}
    found = {arm: {r: p for r, p in runs.items() if r in RUNS} for arm, runs in arms(task.slug, root=root).items()
             if arm.startswith("jev-k")}
    found = {arm: runs for arm, runs in found.items() if len(runs) >= 2}
    if not found:
        return []
    records = {arm: {r: read_by_id(p) for r, p in sorted(runs.items())} for arm, runs in found.items()}
    # Score only items answered in every run of every arm, so arms are compared on the same items.
    common = sorted(set(items).intersection(*(set(rows) for runs in records.values() for rows in runs.values())))
    draws = _resamples(len(common))
    baseline = "jev-k1" if "jev-k1" in records else None
    near_tie = None
    if baseline:
        first = records[baseline][min(records[baseline])]
        near_tie = {i: (m := _margin(first[i])) is not None and m < NEAR_TIE for i in common}
    out: List[dict] = []
    per_item: Dict[tuple, List[float]] = {}

    for arm in sorted(records, key=arm_order):
        runs = records[arm]
        for rule in RULES:
            ratings = [[pool(slots(rows[i]), task.options, rule) for rows in runs.values()] for i in common]
            whole = multi_rater(ratings, task.options)
            boot = [multi_rater([ratings[j] for j in draw], task.options)["ac1"] for draw in draws]
            per_item[(arm, rule)] = boot
            changed = [len(set(r)) > 1 for r in ratings]
            flips = [sum(a != b for a, b in itertools.combinations(r, 2)) / (len(r) * (len(r) - 1) / 2)
                     for r in ratings]
            sds = []
            for i, r in zip(common, ratings):
                modal = Counter(r).most_common(1)[0][0]
                probs = [mean_probabilities(slots(rows[i]), task.options) for rows in runs.values()]
                if modal is not None and all(probs):
                    sds.append(statistics.pstdev(p[modal] for p in probs))
            gold = [items[i]["metadata"]["reference_label"] for i in common]
            accuracy = statistics.mean(sum(r[run] == g for r, g in zip(ratings, gold)) / len(common)
                                       for run in range(len(runs)))
            row = {"kind": "stability", "task": task.slug, "arm": arm, "k": arm_k(arm), "rule": rule,
                   "runs": sorted(runs), "n": len(common), **whole, "ac1_low": _interval(boot)[0],
                   "ac1_high": _interval(boot)[1], "changed": sum(changed),
                   "pair_flip_rate": statistics.mean(flips),
                   "probability_sd": statistics.mean(sds) if sds else None, "accuracy": accuracy}
            if near_tie is not None and sum(changed):
                row["changed_near_tie_share"] = sum(c and near_tie[i] for c, i in zip(changed, common)) / sum(changed)
            out.append(row)
        usage = [r.get("usage") or {} for rows in runs.values() for r in rows.values()]
        tokens = [u["input_tokens"] for u in usage if u.get("input_tokens")]
        latency = sorted(r["latency_ms"] for rows in runs.values() for r in rows.values()
                         if r.get("latency_ms") is not None)
        out.append({"kind": "stability_cost", "task": task.slug, "arm": arm, "k": arm_k(arm),
                    "requests": len(usage), "input_tokens_mean": statistics.mean(tokens) if tokens else None,
                    "latency_p50": latency[len(latency) // 2] if latency else None})

    if baseline:
        for arm in sorted(records, key=arm_order):
            if arm == baseline:
                continue
            for rule in RULES:
                diffs = [a - b for a, b in zip(per_item[(arm, rule)], per_item[(baseline, rule)])]
                point = next(r["ac1"] for r in out if r["kind"] == "stability" and r["arm"] == arm
                             and r["rule"] == rule) - next(r["ac1"] for r in out if r["kind"] == "stability"
                                                           and r["arm"] == baseline and r["rule"] == rule)
                low, high = _interval(diffs)
                out.append({"kind": "stability_paired", "task": task.slug, "arm": arm, "versus": baseline,
                            "rule": rule, "n": len(common), "ac1_diff": point, "ci_low": low, "ci_high": high})
    return out


def replay(task: Task, *, root: Path = ROOT) -> Optional[Path]:
    rows = analyse(task, root=root)
    if not rows:
        return None
    path = Path(root) / "studies" / f"{task.slug}-stability.jsonl"
    write_rows(path, rows)
    return path
