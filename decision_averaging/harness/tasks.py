"""A task: one set of items, its single choice question and its ordered options.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/tasks.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


ROOT = Path(__file__).resolve().parents[2]
QUESTION_NAME = "Decision"


@dataclass(frozen=True)
class Task:
    slug: str
    semantics: str
    question: str
    options: Tuple[str, ...]
    descriptions: Dict[str, str]
    root: Path = ROOT

    @classmethod
    def load(cls, slug: str, *, root: Path = ROOT) -> "Task":
        data = yaml.safe_load((Path(root) / "tasks" / slug / "question.yaml").read_text(encoding="utf-8"))
        options = tuple(data["options"])
        return cls(slug=slug, semantics=data["semantics"], question=data["question"], options=options,
                   descriptions={o: data["descriptions"][o] for o in options}, root=Path(root))

    @property
    def dir(self) -> Path:
        return self.root / "tasks" / self.slug

    @property
    def items_path(self) -> Path:
        return self.dir / "items.jsonl"

    def criteria(self) -> Dict[str, str]:
        """The wire ``criteria``: each option, in order, mapped to its description."""
        return {option: self.descriptions[option] for option in self.options}

    def wire_questions(self) -> Dict[str, dict]:
        return {QUESTION_NAME: {"type": "choice", "instructions": self.question,
                                "criteria": self.criteria()}}

    def load_items(self) -> List[dict]:
        with open(self.items_path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]
