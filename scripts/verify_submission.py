#!/usr/bin/env python
"""Check the submission is actually complete, rather than assuming it is.

Verifies the things the brief asks for: documents ingested, facts grounded in
their sources, cross-document relationships, and a live example of each of the
four required cases. Exits non-zero if anything is missing, so it can gate a
commit.

    python scripts/verify_submission.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factlayer.cases import build_cases      # noqa: E402
from factlayer.config import get_settings    # noqa: E402
from factlayer.db import Store               # noqa: E402

OK, BAD = "  ok  ", " MISS "


def main() -> int:
    store = Store(get_settings().db_path)
    stats = store.stats()

    # Empty database is not a failing corpus, it is an un-run one. Say so, rather
    # than printing fourteen misses that all mean the same thing.
    if stats["documents"] == 0:
        print("No documents ingested yet. Build the corpus first:\n"
              "    FACTLAYER_PROVIDER=replay factlayer ingest data_raw/starter-datasets/*/*.pdf")
        return 2

    cases = build_cases(store, per_case=3)
    failures: list[str] = []

    def check(label: str, passed: bool, detail: str = "") -> None:
        print(f"[{OK if passed else BAD}] {label}{'  — ' + detail if detail else ''}")
        if not passed:
            failures.append(label)

    print("=== corpus ===")
    docs = store.query("SELECT filename, status, n_pages FROM documents ORDER BY ingested_at")
    for doc in docs:
        n = store.one("SELECT COUNT(*) AS n FROM facts WHERE doc_id=(SELECT id FROM documents WHERE filename=?)",
                      (doc["filename"],))["n"]
        print(f"        {doc['status']:8} {doc['filename'][:52]:54} {doc['n_pages']:4}p  {n:5} facts")

    check("every document ingested cleanly",
          all(d["status"] == "ready" for d in docs),
          f"{sum(1 for d in docs if d['status'] != 'ready')} not ready")
    check("at least three documents", len(docs) >= 3, f"{len(docs)} documents")

    print("\n=== facts and grounding ===")
    grounded_pct = 100 * stats["facts_grounded"] / max(stats["facts"], 1)
    check("facts extracted", stats["facts"] > 200, f"{stats['facts']:,}")
    check("most facts grounded in their source", grounded_pct >= 75, f"{grounded_pct:.1f}%")
    ungrounded_no_evidence = store.one(
        "SELECT COUNT(*) AS n FROM facts WHERE evidence_text IS NULL OR evidence_text = ''")["n"]
    check("every fact carries evidence text", ungrounded_no_evidence == 0,
          f"{ungrounded_no_evidence} without evidence")
    no_page = store.one("SELECT COUNT(*) AS n FROM facts WHERE page IS NULL OR page < 1")["n"]
    check("every fact cites a page", no_page == 0, f"{no_page} without a page")

    print("\n=== cross-document relationships ===")
    check("relations exist", stats["relations"] > 100, f"{stats['relations']:,}")
    check("relations span documents", stats["relations_cross_doc"] > 20,
          f"{stats['relations_cross_doc']:,} cross-document")

    print("\n=== the four required cases ===")
    for key, label in (
        ("corroboration", "case 1: corroborated across documents, expressed differently"),
        ("contradiction", "case 2: a genuine or likely contradiction"),
        ("reconciled", "case 3: apparent contradiction explained by context"),
    ):
        examples = cases[key]["examples"]
        best = examples[0] if examples else None
        detail = ""
        if best:
            detail = (f"{best['a']['metric_raw'][:34]} | "
                      f"{'cross-doc' if best['cross_doc'] else 'same doc'} | {best['method']}")
        check(label, bool(examples), detail or "none found")

    failure = cases["failure"]
    summary = failure.get("summary", {})
    check("case 4: extraction failures recorded and explained",
          bool(failure.get("quarantine_reasons")),
          f"{summary.get('quarantined', 0)} quarantined across "
          f"{len(failure.get('quarantine_reasons', []))} distinct reasons")

    print("\n=== dynamic schema ===")
    check("metric vocabulary accumulated", stats["distinct_metrics"] > 50,
          f"{stats['distinct_metrics']:,} metrics")
    check("qualifier keys accumulated from documents", stats["distinct_qualifiers"] >= 10,
          f"{stats['distinct_qualifiers']} qualifier keys")

    print()
    if failures:
        print(f"INCOMPLETE — {len(failures)} check(s) failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
