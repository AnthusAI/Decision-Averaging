"""``da``: run and score the pooled-question benchmark.

    da answer 3 proofwriter-owa --run 1                      # dry run: prints the price, sends nothing
    da answer 3 proofwriter-owa --run 1 --confirm --max-requests 1800
    da answer jev-perm3 emotion --run 1                      # arms: jev-k<k>, jev-perm<k>, jev-para<k>
    da replay && da report                                    # rescore from the records, write RESULTS.md
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import List, Optional

import yaml

from hard_decisions import answering
from hard_decisions.cli import _code_version, _machine
from hard_decisions.record import append_manifest, read_record
from hard_decisions.tasks import Task

from decision_averaging import analysis, report
from decision_averaging.pooled import arm_k, make_engine

ROOT = analysis.ROOT
TASKS = ("proofwriter-owa", "proofwriter-cwa", "emotion")
JEV_USD_PER_INPUT_TOKEN = answering.JEV_USD_PER_INPUT_TOKEN
TOKENS_FIRST_COPY, TOKENS_PER_EXTRA_COPY = 620, 175   # measured in Hard-Decisions (1 vs 10 copies), 2026-10-01


def arm_name(value: str) -> str:
    """``3`` means ``jev-k3`` (identical copies); otherwise an arm name such as ``jev-perm3``."""
    arm = f"jev-k{value}" if value.isdigit() else value
    arm_k(arm)
    return arm


def wordings(task: Task) -> Optional[List[str]]:
    path = task.dir / "variants.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def _engine(arm: str, task: Task):
    from hard_decisions.engines.jev import JevEngine
    return make_engine(arm, JevEngine(), wordings(task))


def _tokens(rows: List[dict]) -> List[float]:
    return [r["usage"]["input_tokens"] for r in rows if (r.get("usage") or {}).get("input_tokens")]


def _price(arm: str, task: Task, todo: List[dict], recorded: List[dict]) -> str:
    k = arm_k(arm)
    measured = _tokens(recorded)
    one = _tokens(read_record(analysis.record_path("jev-k1", 1, task.slug)))
    first = sum(one) / len(one) if one else TOKENS_FIRST_COPY
    if measured:
        each, basis = sum(measured) / len(measured), f"measured from {len(measured)} requests"
    else:
        each = first + TOKENS_PER_EXTRA_COPY * (k - 1)
        basis = (f"estimated from jev-k1's measured {first:.0f} tokens" if one else "estimated from the 1-vs-10-copy probe") \
            + f" + {TOKENS_PER_EXTRA_COPY} per extra copy" * (k > 1)
    tokens = each * len(todo)
    return f"{len(todo)} requests, ~{tokens:,.0f} input tokens, ~${tokens * JEV_USD_PER_INPUT_TOKEN:.4f} ({basis})"


def cmd_answer(args) -> int:
    task = Task.load(args.task, root=ROOT)
    engine = _engine(args.arm, task)
    path = analysis.record_path(engine.name, args.run, task.slug)
    todo = answering.pending(task.load_items(), path, args.limit)
    print(f"{engine.name} run {args.run} on {task.slug}: {len(todo)} items still to answer")
    print(f"price: {_price(engine.name, task, todo, read_record(path))}")
    if not args.confirm:
        print("dry run: nothing sent. Rerun with --confirm --max-requests N.")
        return 0
    if args.max_requests is None or len(todo) > args.max_requests:
        print(f"refusing: --max-requests must be given and at least {len(todo)}", file=sys.stderr)
        return 2
    started_at = answering.utc_now()
    stats = asyncio.run(answering.run(engine, task, todo, path, concurrency=args.concurrency))
    append_manifest(path, {"engine": engine.name, "k": engine.k, "run": args.run, "task": task.slug,
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
    p.add_argument("arm", type=arm_name, help="3 (= jev-k3), or jev-k<k> / jev-perm<k> / jev-para<k>")
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
