"""Draw study 3's 1,000 items per ProofWriter task: tasks/<task>/stability-ids.txt.

Proportional to the full 1,800-item sample's (depth, gold label) groups, largest remainder first, ties broken by
group order; within each group, ``random.Random(0)`` picks from the ids in sorted order. Run once, before any
study 3 run; the committed id lists are what the study uses.

    python scripts/draw_stability_items.py
"""
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1000


def draw(task: str) -> list:
    groups = defaultdict(list)
    for line in open(ROOT / "tasks" / task / "items.jsonl", encoding="utf-8"):
        item = json.loads(line)
        groups[(item["metadata"]["depth"], item["metadata"]["reference_label"])].append(item["id"])
    keys = sorted(groups)
    total = sum(len(v) for v in groups.values())
    exact = {k: SIZE * len(groups[k]) / total for k in keys}
    take = {k: int(exact[k]) for k in keys}
    for k in sorted(keys, key=lambda k: (-(exact[k] - take[k]), keys.index(k)))[:SIZE - sum(take.values())]:
        take[k] += 1
    rng = random.Random(0)
    return sorted(i for k in keys for i in rng.sample(sorted(groups[k]), take[k]))


def main() -> None:
    for task in ("proofwriter-owa", "proofwriter-cwa"):
        ids = draw(task)
        (ROOT / "tasks" / task / "stability-ids.txt").write_text("\n".join(ids) + "\n", encoding="utf-8")
        print(f"{task}: {len(ids)} ids")


if __name__ == "__main__":
    main()
