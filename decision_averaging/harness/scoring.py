"""Small helpers for writing scored rows.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/scoring.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List


def _sort_key(value: str):
    head = value.split("-")[0].rstrip("+")
    return (0, int(head)) if head.isdigit() else (1, value)


def write_rows(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
