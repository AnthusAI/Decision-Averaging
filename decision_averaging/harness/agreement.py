"""Test-retest agreement: percent agreement, Cohen's kappa and Gwet's AC1.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/agreement.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Dict, Optional, Sequence, Tuple


Pair = Tuple[Optional[str], Optional[str]]


def coefficients(pairs: Sequence[Pair], categories: Sequence[str]) -> Dict[str, float]:
    """Percent agreement, Cohen's kappa and Gwet's AC1 for two runs' choices. An invalid answer
    (None) is its own category, so an invalid that repeats counts as agreement."""
    cats = list(categories) + ([None] if any(a is None or b is None for a, b in pairs) else [])
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    kappa_chance = sum(first[c] / n * second[c] / n for c in cats)
    prevalence = [(first[c] + second[c]) / (2 * n) for c in cats]
    ac1_chance = sum(p * (1 - p) for p in prevalence) / (len(cats) - 1)

    def corrected(chance: float) -> float:
        return 1.0 if chance >= 1 else (observed - chance) / (1 - chance)

    return {"agreement": observed, "kappa": corrected(kappa_chance), "ac1": corrected(ac1_chance)}


def bootstrap_ac1(pairs: Sequence[Pair], categories: Sequence[str], *, resamples: int = 1000,
                  seed: int = 0) -> Tuple[float, float]:
    rng = random.Random(seed)
    values = sorted(coefficients([pairs[rng.randrange(len(pairs))] for _ in pairs], categories)["ac1"]
                    for _ in range(resamples))
    return values[int(0.025 * resamples)], values[int(0.975 * resamples) - 1]
