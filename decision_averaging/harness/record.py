"""Answer records: gzip JSONL rows, appended as they arrive, plus a run manifest beside each.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/record.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping


REQUIRED = ("id", "model", "usage", "latency_ms", "answers")


def manifest_path(path: Path) -> Path:
    return Path(path).with_name(Path(path).name.replace(".jsonl.gz", ".runs.jsonl"))


def append_manifest(path: Path, entry: Mapping) -> None:
    target = manifest_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def read_record(path: Path) -> List[Dict]:
    if not Path(path).exists():
        return []
    rows: List[Dict] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_by_id(path: Path) -> Dict[str, Dict]:
    return {row["id"]: row for row in read_record(path)}


def append_rows(path: Path, rows: Iterable[Mapping]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "at", encoding="utf-8") as handle:
        for row in rows:
            missing = [f for f in REQUIRED if f not in row]
            if missing:
                raise ValueError(f"record row {row.get('id')!r} is missing {missing}")
            handle.write(json.dumps(row, sort_keys=True) + "\n")
