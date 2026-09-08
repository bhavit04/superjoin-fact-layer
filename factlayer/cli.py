"""Command line entry points: ingest, serve, inspect."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .cases import build_cases
from .config import get_settings
from .db import Store
from .pipeline import ingest, relink, renormalize


def _progress(stage: str, message: str, detail: dict) -> None:
    print(f"  [{stage:<11}] {message}", flush=True)


async def _ingest_all(paths: list[Path], budget: int) -> int:
    settings = get_settings()
    store = Store(settings.db_path)
    print(f"provider={settings.provider} model={settings.model} db={settings.db_path}")
    failures = 0
    for path in paths:
        if not path.exists():
            print(f"! {path} does not exist", file=sys.stderr)
            failures += 1
            continue
        print(f"\n=== {path.name} ===")
        try:
            result = await ingest(store, path, settings=settings, progress=_progress,
                                  adjudication_budget=budget)
        except Exception as exc:
            print(f"! failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(
            f"  -> {result.facts_stored} facts ({result.facts_grounded} grounded), "
            f"{result.quarantined} quarantined, {result.relations_written} relations "
            f"in {result.duration_s}s"
        )
        if result.by_kind:
            print(f"     {result.by_kind}")
        for note in result.notes:
            print(f"     note: {note}")
    print("\n" + json.dumps(store.stats(), indent=2))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="factlayer", description="Cross-document fact knowledge layer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="ingest one or more PDFs")
    p_ingest.add_argument("paths", nargs="+", type=Path)
    p_ingest.add_argument("--budget", type=int, default=140,
                          help="max pairs sent for LLM adjudication per document")

    p_serve = sub.add_parser("serve", help="run the API and UI")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")

    sub.add_parser("renormalize",
                   help="re-parse stored values and periods in place (no PDFs, no API)")

    p_relink = sub.add_parser(
        "relink", help="recompute all relations from stored facts (no re-extraction)")
    p_relink.add_argument("--budget", type=int, default=60,
                          help="max pairs sent for LLM adjudication")

    sub.add_parser("stats", help="print knowledge layer statistics")

    p_cases = sub.add_parser("cases", help="print the four required cases")
    p_cases.add_argument("--json", action="store_true", help="emit raw JSON")

    sub.add_parser("reset", help="delete the database and start over")

    args = parser.parse_args(argv)
    settings = get_settings()

    if args.command == "ingest":
        return asyncio.run(_ingest_all(args.paths, args.budget))

    if args.command == "serve":
        import uvicorn
        uvicorn.run("factlayer.api:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.command == "renormalize":
        result = renormalize(Store(settings.db_path), progress=_progress)
        print(f"  -> {result['changed']} of {result['facts']} facts changed")
        return 0

    if args.command == "relink":
        store = Store(settings.db_path)
        result = asyncio.run(relink(store, settings=settings, adjudication_budget=args.budget,
                                    progress=_progress))
        print(f"\n  -> {result.relations_written} relations from {result.facts_stored} facts "
              f"in {result.duration_s}s")
        print(f"     {result.by_kind}")
        for note in result.notes:
            print(f"     note: {note}")
        return 0

    if args.command == "stats":
        print(json.dumps(Store(settings.db_path).stats(), indent=2))
        return 0

    if args.command == "cases":
        cases = build_cases(Store(settings.db_path))
        if args.json:
            print(json.dumps(cases, indent=2, default=str))
        else:
            _print_cases(cases)
        return 0

    if args.command == "reset":
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(settings.db_path) + suffix)
            if candidate.exists():
                candidate.unlink()
        print(f"removed {settings.db_path}")
        return 0

    return 1


def _print_cases(cases: dict) -> None:
    for key in ("corroboration", "contradiction", "reconciled"):
        block = cases.get(key, {})
        print(f"\n{'=' * 78}\n{block.get('title', key)}\n{'=' * 78}")
        examples = block.get("examples") or []
        if not examples:
            print("  (none found in the current knowledge layer)")
            continue
        for i, relation in enumerate(examples[:2], 1):
            a, b = relation["a"], relation["b"]
            print(f"\n  [{i}] {relation['kind']}  score={relation['score']}  "
                  f"method={relation['method']}  dimension={relation.get('dimension') or '-'}")
            for label, fact in (("A", a), ("B", b)):
                print(f"    {label}: {fact['subject_raw']} | {fact['metric_raw']} = {fact['value_raw']}"
                      f"  [{fact.get('period_label') or 'no period'}]")
                print(f"       {fact['doc_filename']} p{fact['page']}")
                print(f"       \"{(fact.get('evidence_text') or '')[:160]}\"")
            print(f"    reasoning: {relation['rationale'][:400]}")

    failure = cases.get("failure", {})
    print(f"\n{'=' * 78}\n{failure.get('title', 'failure')}\n{'=' * 78}")
    print(json.dumps(failure.get("summary", {}), indent=2))
    for reason in failure.get("quarantine_reasons", []):
        print(f"  {reason['reason']}: {reason['n']}")


if __name__ == "__main__":
    raise SystemExit(main())
