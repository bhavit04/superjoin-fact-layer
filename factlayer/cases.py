"""Select the four required cases from whatever is in the store.

Each case is a ranking over live relations, so a different corpus produces
different examples through the same code. Nothing is hard-coded to a document.
"""
from __future__ import annotations

import json
from typing import Any

from .db import Store

CASE_TITLES = {
    "corroboration": "A fact corroborated across documents, expressed differently",
    "contradiction": "A genuine or likely contradiction",
    "reconciled": "An apparent contradiction explained by context",
    "failure": "Extraction and reasoning failures we found",
}


def build_cases(store: Store, per_case: int = 4) -> dict[str, Any]:
    return {
        "corroboration": {
            "title": CASE_TITLES["corroboration"],
            "examples": _rank(store, "CORROBORATES", _corroboration_score, per_case),
        },
        "contradiction": {
            "title": CASE_TITLES["contradiction"],
            "examples": _rank(store, "CONTRADICTS", _contradiction_score, per_case),
        },
        "reconciled": {
            "title": CASE_TITLES["reconciled"],
            "examples": _rank(store, "RECONCILED", _reconciled_score, per_case),
        },
        "failure": {
            "title": CASE_TITLES["failure"],
            **_failures(store),
        },
    }


# --- ranking -----------------------------------------------------------------

def _load(store: Store, kind: str) -> list[dict]:
    rows = store.query(
        "SELECT * FROM relations WHERE kind = ? ORDER BY cross_doc DESC, score DESC LIMIT 600",
        (kind,),
    )
    facts = store.get_facts([r["fact_a"] for r in rows] + [r["fact_b"] for r in rows])
    out = []
    for relation in rows:
        a, b = facts.get(relation["fact_a"]), facts.get(relation["fact_b"])
        if not a or not b:
            continue
        try:
            relation["detail"] = json.loads(relation.pop("detail_json") or "{}")
        except (TypeError, ValueError):
            relation["detail"] = {}
        relation["a"], relation["b"] = _shape(store, a), _shape(store, b)
        out.append(relation)
    return out


def _rank(store: Store, kind: str, scorer, limit: int) -> list[dict]:
    scored = [(scorer(r), r) for r in _load(store, kind)]
    scored.sort(key=lambda pair: -pair[0])
    return [{**relation, "case_score": round(score, 3)} for score, relation in scored[:limit] if score > 0]


def _obs(relation: dict) -> dict:
    return (relation.get("detail") or {}).get("observation") or {}


def _corroboration_score(relation: dict) -> float:
    """Rank on surface difference: two documents printing the same string is a
    weaker demonstration than "Rs. 8,142 Mn" against "INR 814 crore"."""
    a, b, obs = relation["a"], relation["b"], _obs(relation)
    if not relation.get("cross_doc"):
        return 0.0
    score = 1.0 + float(relation.get("score") or 0)
    if a["value_raw"].strip().lower() != b["value_raw"].strip().lower():
        score += 1.4                                   # written differently
    if (a.get("value_unit") or "") != (b.get("value_unit") or ""):
        score += 0.8                                   # different unit tags
    if a["metric_raw"].strip().lower() != b["metric_raw"].strip().lower():
        score += 1.0                                   # named differently
    if (a.get("period_label") or "").lower() != (b.get("period_label") or "").lower():
        score += 0.8                                   # same period, said differently
    rel_diff = obs.get("rel_diff")
    if rel_diff is not None and rel_diff > 0:
        score += 0.6                                   # agreement survived a real rounding gap
    score += 0.5 * min(a.get("confidence") or 0, b.get("confidence") or 0)
    return score


def _contradiction_score(relation: dict) -> float:
    """Reward conflicts that are large, cross-document, and confirmed."""
    obs = _obs(relation)
    score = 1.0 + 1.5 * float(relation.get("score") or 0)
    if relation.get("cross_doc"):
        score += 1.5
    if (relation.get("detail") or {}).get("adjudicated"):
        score += 1.0                                   # a model confirmed the rule verdict
    rel_diff = obs.get("rel_diff")
    if rel_diff is not None:
        score += min(1.5, rel_diff * 4)                # bigger gaps are more convincing
    if obs.get("period_relation") == "EQUAL":
        score += 1.2                                   # same period is the strongest case
    if not obs.get("qualifier_deltas"):
        score += 0.8                                   # nothing stated explains it away
    # If the arithmetic itself suspected a unit or scale problem, this is a weak
    # example of a contradiction however confident the adjudicator sounded.
    if any("factor of 10" in h or "scale" in h or "unit" in h
           for h in (obs.get("hypotheses") or [])):
        score -= 2.5
    if obs.get("period_relation") in {"CONTAINS", "CONTAINED_BY"}:
        score -= 1.5                                   # nested periods rarely conflict
    score += 0.5 * min(relation["a"].get("confidence") or 0, relation["b"].get("confidence") or 0)
    return score


def _reconciled_score(relation: dict) -> float:
    """Rank pairs that looked like conflicts until context resolved them."""
    obs = _obs(relation)
    if not relation.get("dimension"):
        return 0.0
    score = 1.0 + float(relation.get("score") or 0)
    if relation.get("cross_doc"):
        score += 1.2
    if (relation.get("detail") or {}).get("adjudicated"):
        score += 0.8
    rel_diff = obs.get("rel_diff")
    if rel_diff is not None and rel_diff > 0.05:
        score += min(1.5, rel_diff * 3)                # it really did look wrong
    if relation.get("dimension") in {"period", "basis", "scope", "unit", "currency"}:
        score += 0.6                                   # a dimension a reader can check
    if (relation.get("detail") or {}).get("model_quote"):
        score += 0.5                                   # the explanation is quote-backed
    return score


# --- case 4 ------------------------------------------------------------------

def _failures(store: Store) -> dict[str, Any]:
    """What actually went wrong, from the system's own bookkeeping."""
    reasons = store.query(
        "SELECT reason, COUNT(*) AS n FROM quarantine GROUP BY reason ORDER BY n DESC"
    )
    samples = store.query(
        "SELECT * FROM quarantine WHERE reason = 'evidence_not_found_in_document' "
        "ORDER BY created_at DESC LIMIT 3"
    )
    table_samples = store.query(
        "SELECT * FROM quarantine WHERE reason IN "
        "('table_association_unverifiable', 'value_present_but_quote_unverifiable') "
        "ORDER BY created_at DESC LIMIT 3"
    )
    for row in table_samples:
        try:
            row["payload"] = json.loads(row.pop("payload_json") or "{}")
        except (TypeError, ValueError):
            row["payload"] = {}
    for row in samples:
        try:
            row["payload"] = json.loads(row.pop("payload_json") or "{}")
        except (TypeError, ValueError):
            row["payload"] = {}

    fuzzy = store.query(
        "SELECT id, doc_id, metric_raw, value_raw, evidence_text, match_ratio, page FROM facts "
        "WHERE match_ratio < 0.995 ORDER BY match_ratio ASC LIMIT 5"
    )
    unresolved_period = store.one(
        "SELECT COUNT(*) AS n FROM facts WHERE period_kind = 'UNKNOWN' OR period_kind IS NULL"
    )["n"]
    total_facts = store.one("SELECT COUNT(*) AS n FROM facts")["n"] or 1
    ungrounded = store.one("SELECT COUNT(*) AS n FROM facts WHERE grounded = 0")["n"]

    overturned = store.query(
        "SELECT * FROM relations WHERE detail_json LIKE '%\"overturned\": true%' "
        "ORDER BY score DESC LIMIT 5"
    )
    overturned_examples = []
    facts = store.get_facts([r["fact_a"] for r in overturned] + [r["fact_b"] for r in overturned])
    for relation in overturned:
        a, b = facts.get(relation["fact_a"]), facts.get(relation["fact_b"])
        if not a or not b:
            continue
        try:
            relation["detail"] = json.loads(relation.pop("detail_json") or "{}")
        except (TypeError, ValueError):
            relation["detail"] = {}
        relation["a"], relation["b"] = _shape(store, a), _shape(store, b)
        overturned_examples.append(relation)

    return {
        "summary": {
            "facts_stored": total_facts,
            "quarantined": sum(r["n"] for r in reasons),
            "ungrounded_stored": ungrounded,
            "fuzzy_grounded": store.one("SELECT COUNT(*) AS n FROM facts WHERE match_ratio < 0.995")["n"],
            "unresolved_period": unresolved_period,
            "unresolved_period_pct": round(100 * unresolved_period / total_facts, 1),
            "rule_verdicts_overturned": len(overturned),
        },
        "quarantine_reasons": reasons,
        "hallucinated_evidence_samples": samples,
        "table_grounding_samples": table_samples,
        "fuzzy_grounding_samples": fuzzy,
        "overturned_examples": overturned_examples,
    }


def _shape(store: Store, fact: dict) -> dict:
    fact = dict(fact)
    try:
        fact["qualifiers"] = {
            k: v for k, v in json.loads(fact.pop("qualifiers_json") or "{}").items()
            if not k.startswith("_")
        }
    except (TypeError, ValueError):
        fact["qualifiers"] = {}
    fact.pop("bbox_json", None)
    document = store.documents_map().get(fact["doc_id"], {})
    fact["doc_filename"] = document.get("filename", "")
    fact["doc_title"] = document.get("title", "")
    return fact
