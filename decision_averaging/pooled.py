"""The pooled engine and the pooling rules.

``PooledEngine`` sends one request whose question set is ``k`` identical copies of the task's
question (``Decision_0`` ... ``Decision_{k-1}``) and records every slot's full answer. Pooling is
applied afterwards, offline, so every rule is scored from the same requests:

- ``vote``: the option most slots chose; a tie goes to the tied option with the higher mean
  probability, then to option order.
- ``mean``: the option with the highest mean probability across slots; a tie goes to option order.

With ``k = 1`` both rules return the single slot's choice.

Preregistration 2 adds arms whose slots differ, still in one request (``make_engine`` builds each from its
arm name):

- ``jev-perm<k>``: one request, the options in ``k`` cyclic rotations of the task's order.
- ``jev-para<k>``: one request, ``k`` question wordings from ``tasks/<task>/variants.yaml``.

Probabilities are keyed by option name, so pooling needs no remapping after a rotation.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hard_decisions.engines.base import EngineAnswer

RULES = ("vote", "mean")
ARM = re.compile(r"^(?P<engine>[a-z]+)-(?P<kind>k|perm|para)(?P<k>\d+)$")
Variants = Callable[[Mapping[str, Any]], List[Mapping[str, Any]]]


def slot_names(k: int) -> List[str]:
    return [f"Decision_{i}" for i in range(k)]


def identical(k: int) -> Variants:
    return lambda question: [question] * k


def rotations(k: int) -> Variants:
    """``k`` cyclic rotations of the option order, evenly spaced: shifts 0, n/k, 2n/k, ... for n options."""
    def build(question: Mapping[str, Any]) -> List[Mapping[str, Any]]:
        options = list(question["criteria"])
        if k > len(options):
            raise ValueError(f"{k} rotations need at least {k} options")
        out = []
        for i in range(k):
            shift = i * len(options) // k
            order = options[shift:] + options[:shift]
            out.append({**question, "criteria": {o: question["criteria"][o] for o in order}})
        return out
    return build


def paraphrases(wordings: Sequence[str]) -> Variants:
    return lambda question: [{**question, "instructions": text} for text in wordings]


class PooledEngine:
    """Wraps any Hard-Decisions engine; one request carrying ``k`` versions of the task question."""

    def __init__(self, inner, k: int, name: str, variants: Optional[Variants] = None):
        if k < 1:
            raise ValueError("k must be at least 1")
        self.inner, self.k, self.name = inner, k, name
        self.variants = variants or identical(k)

    def _versions(self, questions: Mapping[str, Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        if len(questions) != 1:
            raise ValueError("a pooled request repeats exactly one question")
        versions = self.variants(next(iter(questions.values())))
        if len(versions) != self.k:
            raise ValueError(f"{self.name} expects {self.k} versions, got {len(versions)}")
        return versions

    async def answer(self, text: str, questions: Mapping[str, Mapping[str, Any]]) -> EngineAnswer:
        versions = self._versions(questions)
        result = await self.inner.answer(text, dict(zip(slot_names(self.k), versions)))
        return EngineAnswer(answers=result.answers, model=result.model, usage=result.usage)


def arm_k(arm: str) -> int:
    match = ARM.match(arm)
    if not match:
        raise ValueError(f"unknown arm {arm!r}; expected e.g. jev-k3, jev-perm3, jev-para3")
    return int(match["k"])


def make_engine(arm: str, inner, wordings: Optional[Sequence[str]] = None) -> PooledEngine:
    """The engine for an arm name. ``wordings`` (the task's ``variants.yaml``) is needed for ``para``."""
    k, kind = arm_k(arm), ARM.match(arm)["kind"]
    if kind == "k":
        return PooledEngine(inner, k, arm)
    if kind == "perm":
        return PooledEngine(inner, k, arm, rotations(k))
    if not wordings or len(wordings) < k:
        raise ValueError(f"{arm} needs at least {k} wordings in the task's variants.yaml")
    return PooledEngine(inner, k, arm, paraphrases(list(wordings)[:k]))


def slots(row: Mapping[str, Any]) -> List[dict]:
    answers = row.get("answers") or {}
    return [answers[name] for name in sorted(answers, key=lambda n: int(n.rsplit("_", 1)[1]))]


def mean_probabilities(answers: Sequence[Mapping[str, Any]], options: Sequence[str]) -> Optional[Dict[str, float]]:
    vectors = [a.get("probabilities") for a in answers]
    if not vectors or any(not v for v in vectors):
        return None
    return {o: sum(v.get(o, 0.0) for v in vectors) / len(vectors) for o in options}


def pool(answers: Sequence[Mapping[str, Any]], options: Sequence[str], rule: str) -> Optional[str]:
    if rule not in RULES:
        raise ValueError(f"unknown pooling rule {rule!r}")
    means = mean_probabilities(answers, options) or {}
    order = {o: i for i, o in enumerate(options)}
    if rule == "mean":
        if not means:
            return None
        return min(options, key=lambda o: (-means[o], order[o]))
    votes = Counter(a.get("choice") for a in answers if a.get("choice") in options)
    if not votes:
        return None
    top = max(votes.values())
    tied = [o for o in options if votes.get(o) == top]
    return min(tied, key=lambda o: (-means.get(o, 0.0), order[o]))
