"""Turn model output into grounded fact rows.

The model proposes; this module verifies. Every proposed fact is checked against
the actual page text before it is allowed into the knowledge layer, and anything
that fails is written to the quarantine table with a reason rather than silently
dropped. Extraction failures you cannot see are worse than extraction failures
you can.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from .db import new_id
from .llm import LLMClient
from .normalize import entities, metrics, periods, units
from .pdf import Chunk, PdfDocument, normalize_ws
from .prompts import EXTRACT_EXAMPLE, EXTRACT_SYSTEM

# Qualifier keys that plausibly carry a time period, in priority order.
PERIOD_KEYS = (
    "period", "period_label", "fiscal_year", "financial_year", "year", "as_of",
    "as_at", "date", "effective_date", "quarter", "reporting_period", "vintage",
)

VALID_FACT_TYPES = {"numeric", "categorical", "temporal", "textual"}


def build_extract_prompt(chunk: Chunk, doc_title: str) -> str:
    return (
        f"{EXTRACT_EXAMPLE}\n\n"
        f"--- Now extract from this real excerpt ---\n"
        f"Document: {doc_title}\n"
        f"Excerpt covers PDF pages {chunk.page_start} to {chunk.page_end}.\n\n"
        f"{chunk.text}\n\n"
        f"Return only the JSON object."
    )


async def extract_chunk(client: LLMClient, chunk: Chunk, doc_title: str) -> list[dict]:
    """Ask the model for facts in one chunk. Returns raw, unvalidated fact dicts."""
    payload = await client.complete_json(
        system=EXTRACT_SYSTEM,
        prompt=build_extract_prompt(chunk, doc_title),
        task="extract_facts",
        max_output_tokens=16384,
        default={"facts": []},
    )
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = payload.get("facts") or payload.get("results") or []
    else:
        raw = []
    return [f for f in raw if isinstance(f, dict)]


def _pick_period_text(qualifiers: dict, evidence: str, fy_start: int | None = None) -> tuple[str, str]:
    """Return (period_text, source) preferring an explicit qualifier over prose."""
    for key in PERIOD_KEYS:
        value = qualifiers.get(key)
        if isinstance(value, str) and value.strip():
            spec = periods.parse_period(value, fy_start)
            if spec.known:
                return value, f"qualifier:{key}"
    # Any qualifier at all whose value parses as a period.
    for key, value in qualifiers.items():
        if isinstance(value, str) and periods.parse_period(value, fy_start).known:
            return value, f"qualifier:{key}"
    spec = periods.parse_period(evidence, fy_start)
    if spec.known:
        return spec.label, "evidence"
    return "", "none"


def metric_support(metric_raw: str, evidence: str) -> float:
    """How much of the metric's own wording appears in its evidence.

    Grounding proves the quote is real; this asks whether the quote actually
    supports the claim being attached to it. A table cell quoted as "Oils and
    Fats 3.6" is real text, but it says nothing about *what* 3.6 measures -- the
    extractor took "weight in CPI-food and beverages" from elsewhere on the page.
    That fact then contradicted the genuine figure, because one number is a
    weight within the food sub-index and the other a weight within all of CPI.

    Returns the fraction of the metric's content words present in the evidence.
    """
    tokens = [t for t in metrics.metric_tokens(metric_raw) if len(t) > 2]
    if not tokens:
        return 1.0
    haystack = " ".join(metrics.metric_tokens(evidence))
    found = sum(1 for t in tokens if t in haystack)
    return round(found / len(tokens), 3)


def _clean_qualifiers(raw: Any) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        key = re.sub(r"[^\w]+", "_", str(key).strip().lower()).strip("_")
        if not key or value in (None, "", [], {}):
            continue
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)
        text = normalize_ws(str(value))
        if text and len(text) <= 300:
            out[key] = text
    return out


def normalize_fact(
    raw: dict,
    *,
    doc_id: str,
    chunk: Chunk,
    pdf: PdfDocument,
    primary_entity: str | None,
    extractor: str,
    fy_start: int | None = None,
) -> tuple[dict | None, str | None]:
    """Validate, ground and normalize one proposed fact.

    Returns ``(fact_row, None)`` on success or ``(None, reason)`` on rejection.
    """
    metric_raw = normalize_ws(str(raw.get("metric") or ""))
    value_raw = normalize_ws(str(raw.get("value") or ""))
    evidence = normalize_ws(str(raw.get("evidence") or ""))

    if not metric_raw:
        return None, "missing_metric"
    if not value_raw:
        return None, "missing_value"
    if len(evidence) < 12:
        return None, "evidence_too_short"
    if len(metric_raw) > 160:
        return None, "metric_too_long"

    # Grounding: the quote must actually exist in the document.
    hint_page = raw.get("page")
    hint_page = int(hint_page) if isinstance(hint_page, (int, float, str)) and str(hint_page).strip().isdigit() else None
    location = pdf.locate_evidence(evidence, hint_page=hint_page, candidate_pages=chunk.pages)
    if location is None:
        return None, _classify_grounding_failure(pdf, chunk, value_raw, metric_raw, hint_page)

    qualifiers = _clean_qualifiers(raw.get("qualifiers"))
    period_text, period_source = _pick_period_text(qualifiers, evidence, fy_start)
    period = periods.parse_period(period_text, fy_start)
    if period_source != "none":
        qualifiers.setdefault("period", period_text)
    qualifiers["_period_source"] = period_source

    unit_hint = normalize_ws(str(raw.get("unit_hint") or ""))
    value = units.parse_value(value_raw, unit_hint=unit_hint or None)

    subject_display, subject_key = entities.resolve_subject(raw.get("subject"), primary_entity)

    fact_type = str(raw.get("fact_type") or "").lower().strip()
    if fact_type not in VALID_FACT_TYPES:
        fact_type = "numeric" if value.number is not None else "textual"

    support = metric_support(metric_raw, location.matched_text or evidence)

    try:
        confidence = float(raw.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = min(1.0, max(0.0, confidence))
    # A fact whose evidence only fuzzily matched is less trustworthy than the
    # model's own confidence suggests.
    confidence *= 0.6 + 0.4 * location.match_ratio
    if location.mode == "fragments":
        confidence *= 0.85
    confidence *= 0.55 + 0.45 * support

    page_label = ""
    try:
        page_label = pdf._doc[location.page - 1].get_label() or str(location.page)
    except Exception:
        page_label = str(location.page)

    return {
        "id": new_id("f"),
        "metric_support": support,
        "doc_id": doc_id,
        "chunk_ordinal": chunk.ordinal,
        "subject_raw": subject_display[:200],
        "subject_key": subject_key[:200],
        "metric_raw": metric_raw,
        "metric_key": metrics.metric_key(metric_raw),
        "metric_cluster": metrics.metric_key(metric_raw),  # refined later by clustering
        "derivative_kind": metrics.derivative_kind(metric_raw),
        "fact_type": fact_type,
        "polarity": "negated" if str(raw.get("polarity", "")).lower() == "negated" else "affirmed",
        "value_raw": value_raw[:300],
        "value_text": value_raw[:300] if value.number is None else None,
        "value_num": value.number,
        "value_low": value.low,
        "value_high": value.high,
        "value_unit": value.unit,
        "value_kind": value.kind,
        "is_range": int(value.is_range),
        "is_approximate": int(value.is_approximate),
        "qualifiers_json": json.dumps(qualifiers, ensure_ascii=False),
        "period_label": period.label or period_text,
        "period_canonical": period.canonical,
        "period_kind": period.kind,
        "period_start": period.start,
        "period_end": period.end,
        "period_is_point": int(period.is_point),
        "evidence_text": location.matched_text[:2000] if location.match_ratio < 1.0 else evidence[:2000],
        "page": location.page,
        "page_label": page_label,
        "bbox_json": json.dumps(location.rects),
        "match_ratio": location.match_ratio,
        "grounding_mode": location.mode,
        "grounded": int(location.verified),
        "confidence": round(confidence, 3),
        "extractor": extractor,
        "created_at": time.time(),
    }, None


def _classify_grounding_failure(
    pdf: PdfDocument, chunk: Chunk, value_raw: str, metric_raw: str, hint_page: int | None
) -> str:
    """Say *why* a fact failed to ground, not just that it did.

    The distinction matters. If neither the value nor the metric appears anywhere
    near the cited page, the model very likely invented the fact. If both appear
    but the quote is not a verifiable span, the model read a table or chart whose
    cells do not extract in reading order -- the fact is probably true, and it is
    the extractor's spatial understanding that failed, not its honesty. Lumping
    those together would hide a fixable engineering problem behind a scary word.
    """
    pages = [p for p in ([hint_page] if hint_page else []) + list(chunk.pages) if p]
    haystack = " ".join(pdf.page_text(p) for p in dict.fromkeys(pages) if 1 <= p <= pdf.page_count)
    haystack = normalize_ws(haystack).lower()
    if not haystack:
        return "evidence_not_found_in_document"

    value_present = bool(value_raw) and value_raw.strip().lower() in haystack
    metric_words = [w for w in re.split(r"[^\w]+", metric_raw.lower()) if len(w) > 3]
    metric_present = bool(metric_words) and all(w in haystack for w in metric_words[:4])

    if value_present and metric_present:
        return "table_association_unverifiable"
    if value_present:
        return "value_present_but_quote_unverifiable"
    return "evidence_not_found_in_document"


# --- credential-free fallback ------------------------------------------------

_SENT_SPLIT = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")
_HEURISTIC_VALUE = re.compile(
    r"(?:(?:Rs\.?|INR|₹|US\$|USD|\$)\s?[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|million|billion|mn|bn|cr|trillion))?"
    r"|[\d,]+(?:\.\d+)?\s*(?:per cent|percent|%|bps|crore|lakh|million|billion|mn|bn))",
    re.IGNORECASE,
)
_STOP_START = re.compile(r"^(?:table|figure|source|note|annex|chart|page)\b", re.IGNORECASE)


def heuristic_extract(chunk: Chunk, limit: int = 12) -> list[dict]:
    """A deliberately simple regex extractor used when no LLM is reachable.

    It exists so the system degrades instead of failing on an unseen PDF with no
    credential. It is genuinely weak -- it guesses the metric from the words
    preceding a number and has no notion of basis or scope -- and facts it
    produces are tagged ``extractor="heuristic"`` so they can be told apart.
    """
    out: list[dict] = []
    page = chunk.page_start
    for line in chunk.text.split("\n"):
        marker = re.match(r"\[\[page (\d+)\]\]", line.strip())
        if marker:
            page = int(marker.group(1))
            continue
        for sentence in _SENT_SPLIT.split(line):
            sentence = normalize_ws(sentence)
            if len(sentence) < 40 or len(sentence) > 400 or _STOP_START.match(sentence):
                continue
            match = _HEURISTIC_VALUE.search(sentence)
            if not match:
                continue
            before = sentence[: match.start()].strip()
            words = [w for w in re.split(r"[^\w%]+", before) if w]
            if len(words) < 2:
                continue
            metric = " ".join(words[-6:]).lower()
            metric = re.sub(r"^(?:and|the|of|in|for|a|an|to|was|were|is|at|by)\s+", "", metric)
            if len(metric) < 4:
                continue
            out.append({
                "subject": "the Company",
                "metric": metric[:120],
                "value": match.group(0),
                "unit_hint": "",
                "fact_type": "numeric",
                "qualifiers": {},
                "polarity": "affirmed",
                "evidence": sentence,
                "page": page,
                "confidence": 0.35,
            })
            if len(out) >= limit:
                return out
    return out
