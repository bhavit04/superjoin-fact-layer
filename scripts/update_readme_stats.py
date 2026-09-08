#!/usr/bin/env python
"""Write current corpus statistics into the README between the STATS markers.

Keeps the numbers in the README honest: they are regenerated from the database
rather than typed in and left to rot.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factlayer.config import get_settings   # noqa: E402
from factlayer.db import Store              # noqa: E402


def main() -> int:
    store = Store(get_settings().db_path)
    stats = store.stats()
    kinds = stats["by_kind"]
    docs = store.query("SELECT id, filename, n_pages FROM documents ORDER BY ingested_at")

    lines = ["| document | pages | facts | grounded |", "|---|---:|---:|---:|"]
    for doc in docs:
        n = store.one("SELECT COUNT(*) AS n FROM facts WHERE doc_id = ?", (doc["id"],))["n"]
        g = store.one("SELECT COUNT(*) AS n FROM facts WHERE doc_id = ? AND grounded = 1", (doc["id"],))["n"]
        pct = f"{100 * g / n:.0f}%" if n else "—"
        lines.append(f"| `{doc['filename']}` | {doc['n_pages']} | {n:,} | {pct} |")

    total_pages = sum(d["n_pages"] or 0 for d in docs)
    grounded_pct = 100 * stats["facts_grounded"] / max(stats["facts"], 1)
    lines += [
        f"| **{len(docs)} documents** | **{total_pages}** | **{stats['facts']:,}** | **{grounded_pct:.0f}%** |",
        "",
        "| relationship | count | |",
        "|---|---:|---|",
        f"| **CORROBORATES** | {kinds.get('CORROBORATES', 0):,} | the same claim, agreeing |",
        f"| **RECONCILED** | {kinds.get('RECONCILED', 0):,} | disagreeing, but a stated difference in context explains it |",
        f"| **CONTRADICTS** | {kinds.get('CONTRADICTS', 0):,} | disagreeing with nothing to explain it |",
        f"| **RELATED** | {kinds.get('RELATED', 0):,} | same metric, different periods — a time series |",
        f"| _of which cross-document_ | {stats['relations_cross_doc']:,} | |",
        "",
        f"The fact schema grew to **{stats['distinct_metrics']:,} metric names** and "
        f"**{stats['distinct_qualifiers']} qualifier keys** across "
        f"**{stats['distinct_entities']:,} subjects** — none of it declared in advance. "
        f"**{stats['quarantined']}** proposed facts were rejected for failing to ground.",
    ]

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    block = "<!--STATS-->\n" + "\n".join(lines) + "\n<!--/STATS-->"
    text = re.sub(r"<!--STATS-->.*?<!--/STATS-->", block, text, flags=re.DOTALL)
    readme.write_text(text, encoding="utf-8")
    print("README statistics updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
