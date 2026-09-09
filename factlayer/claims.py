"""Group facts into claims: everything every source says about one quantity.

Relations are pairwise, which answers "do these two agree?" but not the question
a reader actually has: what does *every* source say about India's current account
deficit for FY2025, and do they line up?

A claim collects every fact sharing a subject, metric and period, reports the
spread across sources, and says whether the pairwise pass already explained the
differences. Pure aggregation over stored data — no model calls.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from .db import Store
from .normalize import units

MIN_SOURCES = 2
AGREEMENT_TOLERANCE = 0.02


def _spread(values: list[float]) -> tuple[str, float]:
    usable = [v for v in values if v is not None]
    if len(usable) < 2:
        return "single", 0.0
    low, high = min(usable), max(usable)
    scale = max(abs(low), abs(high))
    gap = 0.0 if scale == 0 else abs(high - low) / scale
    return ("agree" if gap <= AGREEMENT_TOLERANCE else "disagree"), gap


def build_claims(
    store: Store, limit: int = 60, only_conflicts: bool = False, query: str = ""
) -> list[dict[str, Any]]:
    """Assemble claims, most consequential first."""
    sql = ("SELECT * FROM facts WHERE metric_cluster IS NOT NULL AND metric_cluster != ''")
    params: list[Any] = []
    if query:
        sql += " AND (metric_raw LIKE ? OR subject_raw LIKE ?)"
        params += [f"%{query}%", f"%{query}%"]

    documents = store.documents_map()
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for fact in store.query(sql, params):
        grouped[(fact["subject_key"], fact["metric_cluster"],
                 fact["period_canonical"] or "")].append(fact)

    # How the pairwise pass judged each pair, so a claim can say why its members
    # differ rather than only that they do.
    verdicts: dict[frozenset, dict] = {}
    for r in store.query("SELECT fact_a, fact_b, kind, dimension FROM relations"):
        verdicts[frozenset((r["fact_a"], r["fact_b"]))] = r

    claims: list[dict[str, Any]] = []
    for (subject_key, cluster, period), facts in grouped.items():
        if len(facts) < MIN_SOURCES:
            continue
        docs = {f["doc_id"] for f in facts}

        numeric = [f for f in facts if f.get("value_num") is not None]
        unit = numeric[0].get("value_unit") if numeric else ""
        comparable = [f for f in numeric if (f.get("value_unit") or "") == (unit or "")]
        status, spread = _spread([f["value_num"] for f in comparable])

        dimensions, kinds = set(), set()
        for i, a in enumerate(facts):
            for b in facts[i + 1:]:
                rel = verdicts.get(frozenset((a["id"], b["id"])))
                if rel:
                    kinds.add(rel["kind"])
                    if rel.get("dimension"):
                        dimensions.add(rel["dimension"])
        if status == "disagree" and "RECONCILED" in kinds and "CONTRADICTS" not in kinds:
            status = "explained"
        if only_conflicts and status not in {"disagree", "explained"}:
            continue

        sources = sorted(facts, key=lambda f: -(f.get("confidence") or 0))[:8]
        claims.append({
            "subject": sources[0]["subject_raw"],
            "metric": max((f["metric_raw"] for f in facts), key=len),
            "period": period or "unresolved",
            "status": status,
            "spread": round(spread, 4),
            "unit": unit,
            "n_facts": len(facts),
            "n_documents": len(docs),
            "dimensions": sorted(dimensions),
            # A wide disagreement across independent sources deserves attention
            # before a narrow one inside a single document.
            "materiality": round(
                spread * (len(docs) ** 0.5) * (2.0 if status == "disagree" else 1.0), 4),
            "sources": [{
                "fact_id": f["id"],
                "value_raw": f["value_raw"],
                "display": (units.humanize(f["value_num"], f.get("value_unit") or "")
                            if f.get("value_num") is not None else f["value_raw"]),
                "document": documents.get(f["doc_id"], {}).get("filename", ""),
                "page": f["page"],
                "period_label": f.get("period_label"),
                "evidence": f.get("evidence_text"),
                "qualifiers": {k: v for k, v in
                               json.loads(f.get("qualifiers_json") or "{}").items()
                               if not k.startswith("_")},
            } for f in sources],
        })

    claims.sort(key=lambda c: (-(c["n_documents"] > 1), -c["materiality"], -c["n_facts"]))
    return claims[:limit]


def claim_stats(claims: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for c in claims:
        counts[c["status"]] += 1
        if c["n_documents"] > 1:
            counts["cross_document"] += 1
    return dict(counts)
