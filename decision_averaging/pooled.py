"""The pooled engine and the pooling rules.

``PooledEngine`` sends one request whose question set is ``k`` identical copies of the task's
question (``Decision_0`` ... ``Decision_{k-1}``) and records every slot's full answer. Pooling is
applied afterwards, offline, so every rule is scored from the same requests:

- ``vote``: the option most slots chose; a tie goes to the tied option with the higher mean
  probability, then to option order.
- ``mean``: the option with the highest mean probability across slots; a tie goes to option order.

With ``k = 1`` both rules return the single slot's choice.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Mapping, Optional, Sequence

from hard_decisions.engines.base import EngineAnswer

RULES = ("vote", "mean")


def slot_names(k: int) -> List[str]:
    return [f"Decision_{i}" for i in range(k)]


class PooledEngine:
    """Wraps any Hard-Decisions engine; ``k`` copies of the one task question per request."""

    def __init__(self, inner, k: int, name: str):
        if k < 1:
            raise ValueError("k must be at least 1")
        self.inner, self.k, self.name = inner, k, name

    async def answer(self, text: str, questions: Mapping[str, Mapping[str, Any]]) -> EngineAnswer:
        if len(questions) != 1:
            raise ValueError("a pooled request repeats exactly one question")
        question = next(iter(questions.values()))
        result = await self.inner.answer(text, {name: question for name in slot_names(self.k)})
        return EngineAnswer(answers=result.answers, model=result.model, usage=result.usage)


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
