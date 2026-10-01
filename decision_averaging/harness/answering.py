"""Ask an engine and append each answer to the record as it arrives. A failed item is retried on the
next run, which skips ids already recorded.

Vendored from Hard-Decisions commit a19776a (``hard_decisions/answering.py``), unchanged except for imports and
the parts this project does not use.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from decision_averaging.harness.base import Engine
from decision_averaging.harness.record import append_rows, read_record
from decision_averaging.harness.tasks import Task


JEV_USD_PER_INPUT_TOKEN = 42 / 1e9   # TypeSafe's published price; output tokens are free


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def pending(items: Sequence[dict], path: Path, limit: Optional[int] = None) -> List[dict]:
    done = {row["id"] for row in read_record(path)}
    todo = [item for item in items if item["id"] not in done]
    return todo[:limit] if limit is not None else todo


async def run(engine: Engine, task: Task, items: Sequence[dict], path: Path, *, concurrency: int = 8,
              max_failures: int = 10) -> Dict[str, int]:
    """Answer ``items`` and append each row as it arrives. Returns counts."""
    questions = task.wire_questions()
    gate = asyncio.Semaphore(concurrency)
    stats = {"answered": 0, "failed": 0}
    stop = asyncio.Event()

    async def one(item: dict) -> None:
        if stop.is_set():
            return
        async with gate:
            if stop.is_set():
                return
            started_at = utc_now()
            started = time.perf_counter()
            try:
                result = await engine.answer(item["text"], questions)
            except Exception as error:  # noqa: BLE001 - a failed item is retried on the next run
                stats["failed"] += 1
                if stats["failed"] >= max_failures:
                    stop.set()
                print(f"  failed {item['id']}: {type(error).__name__}")
                return
            append_rows(path, [{"id": item["id"], "model": result.model or engine.name, "usage": result.usage,
                                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                                "started_at": started_at,
                                "answers": result.answers}])
            stats["answered"] += 1

    await asyncio.gather(*(one(item) for item in items))
    return stats
