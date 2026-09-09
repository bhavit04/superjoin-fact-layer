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

    # An unmatched shell glob arrives as a literal path, so "no such dataset" would
    # otherwise surface as an ingest of zero files reporting an empty corpus. Say
    # what is missing instead.
    if not any(p.exists() for p in paths):
        print("Nothing to ingest -- none of these paths exist:", file=sys.stderr)
        for p in paths:
            print(f"    {p}", file=sys.stderr)
        if any("starter-datasets" in str(p) for p in paths):
            print("\nThe starter PDFs are not committed to this repository. Unzip the dataset\n"
                  "at data_raw/starter-datasets/ and run this again.", file=sys.stderr)
        return 2

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

    sub.add_parser("doctor", help="check configuration and report which models your key can reach")

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

    if args.command == "doctor":
        return _doctor(settings)

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


def _doctor(settings) -> int:
    """Tell the user whether their setup will actually work, and what to change.

    Free-tier keys differ in which models they can reach -- Google refuses older
    models to newly issued keys -- so "it works on my machine" is not a safe
    assumption here. This probes the configured chain and reports what is usable.
    """
    import httpx

    from .llm import DiskCache, LLMClient

    print(f"provider     {settings.provider}")
    print(f"model        {settings.model}")
    print(f"fallbacks    {', '.join(settings.fallback_models) or '(none)'}")
    print(f"database     {settings.db_path}")
    cache = DiskCache(settings.cache_dir)
    print(f"cache        {cache.size()} cached responses at {settings.cache_dir}")

    store = Store(settings.db_path)
    stats = store.stats()
    print(f"knowledge    {stats['documents']} documents, {stats['facts']:,} facts, "
          f"{stats['relations']:,} relations")

    if not settings.api_key:
        print("\nNo API key set.")
        print("  Cached documents still replay: FACTLAYER_PROVIDER=replay factlayer ingest <pdf>")
        print(f"  For new PDFs, set {settings.provider.upper()}_API_KEY in .env")
        return 0

    print(f"\nProbing models reachable with this {settings.provider} key...")
    client = LLMClient(settings)
    reachable: list[str] = []
    for model in client._models:
        try:
            if settings.provider == "gemini":
                response = httpx.post(
                    "https://generativelanguage.googleapis.com/v1beta/interactions",
                    params={"key": settings.api_key}, timeout=45,
                    json={"model": model, "input": "ok",
                          "generation_config": {"max_output_tokens": 16, "thinking_level": "low"}},
                )
            else:
                print(f"  {model:28} (live probe not implemented for {settings.provider})")
                continue
        except Exception as exc:
            print(f"  {model:28} unreachable — {type(exc).__name__}")
            continue
        if response.status_code == 200:
            print(f"  {model:28} OK")
            reachable.append(model)
        elif response.status_code == 429:
            limit = ""
            if "limit:" in response.text:
                limit = response.text.split("limit:")[1].split(",")[0].strip()
            print(f"  {model:28} out of quota today (limit {limit or '?'})")
        elif response.status_code == 404:
            print(f"  {model:28} not available to this key")
        else:
            print(f"  {model:28} HTTP {response.status_code}")

    if reachable:
        print(f"\nReady. Ingestion will use {reachable[0]}.")
    else:
        print("\nNo model is currently usable with this key.")
        print("  Quota resets daily, or create a key under a different Google Cloud project.")
        print("  Meanwhile: FACTLAYER_PROVIDER=replay reproduces the committed knowledge layer.")
    return 0


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
