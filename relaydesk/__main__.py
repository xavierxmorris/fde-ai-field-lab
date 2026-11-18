"""Command-line entrypoint. Run from the checkout with python -m relaydesk."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import review
from .engine import DATA, Engine
from .evaluation import evaluate, format_report


def parser():
    p = argparse.ArgumentParser(description="RelayDesk offline policy-lookup lab (synthetic data only)")
    p.add_argument("--data-dir", type=Path, default=DATA, help="directory with synthetic JSONL fixtures")
    p.add_argument("--db", type=Path, default=Path(".relaydesk/review.sqlite3"),
                   help="local single-user queue (default: .relaydesk/review.sqlite3)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="run three stops without writing a database")
    triage = sub.add_parser("triage", help="preview a lookup without saving it")
    triage.add_argument("--trace", action="store_true", help="include tokens and decision scores")
    submit = sub.add_parser("submit", help="record a lookup for manual handling or draft review")
    submit.add_argument("id", help="caller-supplied idempotency key")
    for action in (triage, submit):
        action.add_argument("tenant", help="northstar or harbor")
        action.add_argument("lookup_date", help="operator-supplied YYYY-MM-DD policy lookup date")
        action.add_argument("question", help="quoted synthetic question")
    sub.add_parser("pending", help="list only drafts awaiting review")
    sub.add_parser("show", help="inspect the saved snapshot and review state").add_argument("id")
    decision = sub.add_parser("review", help="record a human decision; never sends or approves a return")
    decision.add_argument("id")
    decision.add_argument("decision", choices=("accept", "reject"))
    decision.add_argument("--note", default="", help="synthetic review note")
    bench = sub.add_parser("eval", help="compare scoped retrieval to gated triage")
    bench.add_argument("--cases", type=Path, help="separate labeled JSONL set (default: acceptance.jsonl)")
    bench.add_argument("--json", action="store_true", help="machine-readable report")
    return p


def demo(engine):
    question = "What is the standard return window?"
    for title, lookups in (
        ("1. Same retailer, opposite sides of the cutover",
         [("northstar", "2025-06-30", question), ("northstar", "2025-07-01", question)]),
        ("2. Same date and question, different retailer", [("harbor", "2025-07-01", question)]),
        ("3. One card cannot answer two topics",
         [("northstar", "2025-07-01", "What is the return window, and how do I report damage?")]),
    ):
        print(title)
        for tenant, day, text in lookups:
            result = engine.triage(tenant, day, text)
            card = result["evidence"]
            answer = f"{card['id']} (v{card['version']}): {card['excerpt']}" if card else result["reason"]
            print(f"  {tenant} @ {day} | {text}\n  -> {result['disposition']}: {answer}")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command in ("demo", "triage", "eval"):
            engine = Engine.load(args.data_dir)
            if args.command == "demo":
                demo(engine)
                return 0
            if args.command == "eval":
                report = evaluate(engine, args.cases or args.data_dir / "acceptance.jsonl")
                print(json.dumps(report, indent=2) if args.json else format_report(report))
                return 0 if report["passed"] else 1
            result = engine.triage(args.tenant, args.lookup_date, args.question, trace=args.trace)
        else:
            with review.open_queue(args.db) as db:
                if args.command == "pending":
                    result = review.pending(db)
                elif args.command == "show":
                    result = review.show(db, args.id)
                elif args.command == "review":
                    result = review.review(db, args.id, args.decision, args.note)
                else:
                    result = review.submit(db, args.id, args.tenant, args.lookup_date, args.question,
                                           lambda *q: Engine.load(args.data_dir).triage(*q))
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"relaydesk: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
