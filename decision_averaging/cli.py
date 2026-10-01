"""``da``: run and score the pooled-question benchmark.

    da answer 3 proofwriter-owa --run 1                      # dry run: prints the price, sends nothing
    da answer 3 proofwriter-owa --run 1 --confirm --max-requests 1800
    da replay && da report                                    # rescore from the records, write RESULTS.md
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List, Optional

from hard_decisions import answering
from hard_decisions.cli import _code_version, _machine
from hard_decisions.record import append_manifest, read_record
from hard_decisions.tasks import Task

from decision_averaging import analysis, report
from decision_averaging.pooled import PooledEngine

ROOT = analysis.ROOT
TASKS = ("proofwriter-owa", "proofwriter-cwa")
JEV_USD_PER_INPUT_TOKEN = answering.JEV_USD_PER_INPUT_TOKEN
TOKENS_FIRST_COPY, TOKENS_PER_EXTRA_COPY = 620, 175   # measured in Hard-Decisions (1 vs 10 copies), 2026-10-01


def _engine(k: int):
    from hard_decisions.engines.jev import JevEngine
    return PooledEngine(JevEngine(), k, f"jev-k{k}")


def _price(k: int, todo: List[dict], recorded: List[dict]) -> str:
    measured = [r["usage"]["input_tokens"] for r in recorded if (r.get("usage") or {}).get("input_tokens")]
    each = sum(measured) / len(measured) if measured else TOKENS_FIRST_COPY + TOKENS_PER_EXTRA_COPY * (k - 1)
    basis = f"measured from {len(measured)} requests" if measured else "estimated from the 1-vs-10-copy probe"
    tokens = each * len(todo)
    return f"{len(todo)} requests, ~{tokens:,.0f} input tokens, ~${tokens * JEV_USD_PER_INPUT_TOKEN:.4f} ({basis})"


def cmd_answer(args) -> int:
    task = Task.load(args.task, root=ROOT)
    engine = _engine(args.k)
    path = analysis.record_path(engine.name, args.run, task.slug)
    todo = answering.pending(task.load_items(), path, args.limit)
    print(f"{engine.name} run {args.run} on {task.slug}: {len(todo)} items still to answer")
    print(f"price: {_price(args.k, todo, read_record(path))}")
    if not args.confirm:
        print("dry run: nothing sent. Rerun with --confirm --max-requests N.")
        return 0
    if args.max_requests is None or len(todo) > args.max_requests:
        print(f"refusing: --max-requests must be given and at least {len(todo)}", file=sys.stderr)
        return 2
    started_at = answering.utc_now()
    stats = asyncio.run(answering.run(engine, task, todo, path, concurrency=args.concurrency))
    append_manifest(path, {"engine": engine.name, "k": args.k, "run": args.run, "task": task.slug,
                           "started_at": started_at, "finished_at": answering.utc_now(),
                           "requested": len(todo), "answered": stats["answered"], "failed": stats["failed"],
                           "concurrency": args.concurrency, "machine": _machine(), "code": _code_version_here()})
    print(f"answered {stats['answered']}, failed {stats['failed']} (rerun to retry failures)")
    return 0 if not stats["failed"] else 1


def _code_version_here() -> dict:
    import subprocess
    run = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout.strip()  # noqa: E731
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain", "--untracked-files=no")),
            "hard_decisions": _code_version()}


def cmd_replay(args) -> int:
    for slug in TASKS:
        path = analysis.replay(Task.load(slug, root=ROOT))
        if path:
            print(f"wrote {path.relative_to(ROOT)}")
    return 0


def cmd_report(args) -> int:
    print(f"wrote {report.write().relative_to(ROOT)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="da")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("answer", help="price (default) or run the k-copy arm on a task")
    p.add_argument("k", type=int)
    p.add_argument("task", choices=TASKS)
    p.add_argument("--run", type=int, required=True, choices=(1, 2))
    p.add_argument("--limit", type=int)
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--max-requests", type=int)
    p.add_argument("--concurrency", type=int, default=4)
    p.set_defaults(func=cmd_answer)
    sub.add_parser("replay", help="rescore every record offline").set_defaults(func=cmd_replay)
    sub.add_parser("report", help="regenerate RESULTS.md").set_defaults(func=cmd_report)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
