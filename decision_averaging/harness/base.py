"""The protocol every engine adapter implements.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/engines/base.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class EngineAnswer:
    answers: Dict[str, dict]
    model: Optional[str] = None
    usage: Optional[dict] = None


@runtime_checkable
class Engine(Protocol):
    name: str

    async def answer(self, text: str, questions: Mapping[str, Mapping[str, Any]]) -> EngineAnswer:
        ...
