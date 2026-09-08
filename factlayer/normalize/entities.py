"""Collapse the many surface forms of a subject onto one key.

Two problems show up in real filings:

1. Legal-suffix noise. "Delhivery Limited", "Delhivery Ltd.", "Delhivery" and
   "DELHIVERY LIMITED" are one entity.
2. Anaphora. Annual reports overwhelmingly say "the Company", "our Company",
   "the Group" or "the Bank" instead of naming themselves. Left alone, every
   document produces its own useless "the company" entity and nothing links.
   These are resolved against the primary entity detected for the document.

Nothing here is specific to a company or a document -- the primary entity is
inferred per document at ingest time from what the extractor actually saw.
"""
from __future__ import annotations

import re
from collections import Counter

LEGAL_SUFFIXES = {
    "limited", "ltd", "private", "pvt", "inc", "incorporated", "corp", "corporation",
    "company", "co", "plc", "llp", "llc", "group", "holdings", "sa", "nv", "ag", "gmbh",
}

LEADING_ARTICLES = {"the", "our", "its", "their"}

# Surface forms that refer back to the document's own subject rather than naming it.
ANAPHORIC = {
    "the company", "our company", "the group", "our group", "the bank", "the issuer",
    "the corporation", "the organisation", "the organization", "we", "us", "the firm",
    "company", "group", "the entity", "the parent", "the reserve bank", "the fund",
    "the staff", "staff",
}

_PUNCT = re.compile(r"[^\w\s&]")
_WS = re.compile(r"\s+")


def normalize_entity(name: str | None) -> str:
    """Lowercase, de-punctuate and strip legal suffixes -> a stable key."""
    if not name:
        return ""
    text = _PUNCT.sub(" ", str(name).lower())
    text = _WS.sub(" ", text).strip()
    if not text:
        return ""
    tokens = text.split()
    while tokens and tokens[0] in LEADING_ARTICLES:
        tokens.pop(0)
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    if not tokens:
        # The name was nothing but suffixes ("the Company") -- keep it recognizable
        # so the anaphora resolver can act on it.
        return _WS.sub(" ", _PUNCT.sub(" ", str(name).lower())).strip()
    return " ".join(tokens)


def is_anaphoric(name: str | None) -> bool:
    if not name:
        return True
    cleaned = _WS.sub(" ", _PUNCT.sub(" ", str(name).lower())).strip()
    return cleaned in ANAPHORIC


def infer_primary_entity(subject_names: list[str]) -> str | None:
    """Guess a document's own subject: the most frequent non-anaphoric entity.

    Frequency is a weak signal on its own, so ties are broken toward longer
    (more specific) names.
    """
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    for raw in subject_names:
        if not raw or is_anaphoric(raw):
            continue
        key = normalize_entity(raw)
        if not key or len(key) < 3:
            continue
        counts[key] += 1
        # Keep the longest surface form we saw for this key as the display name.
        if key not in display or len(raw) > len(display[key]):
            display[key] = raw.strip()
    if not counts:
        return None
    best = max(counts.items(), key=lambda kv: (kv[1], len(kv[0])))
    return display.get(best[0], best[0])


def resolve_subject(raw: str | None, primary_entity: str | None) -> tuple[str, str]:
    """Return (display_name, key) for a subject, resolving anaphora when possible."""
    if is_anaphoric(raw) and primary_entity:
        return primary_entity, normalize_entity(primary_entity)
    display = (raw or "").strip() or (primary_entity or "unknown")
    return display, normalize_entity(display) or "unknown"


def entities_match(key_a: str, key_b: str) -> bool:
    """Exact match, or one key being a strict token-prefix of the other.

    "delhivery" matches "delhivery" and "delhivery supply chain" is treated as a
    *different* entity -- a subsidiary is not its parent. Only whole-key equality
    and single-token containment of a multi-word key count.
    """
    if not key_a or not key_b:
        return False
    if key_a == key_b:
        return True
    ta, tb = key_a.split(), key_b.split()
    if len(ta) == 1 and len(tb) == 1:
        return ta[0] == tb[0]
    # "india" vs "indian economy": share the head token and one side is a single word.
    if len(ta) == 1 and ta[0] == tb[0]:
        return True
    if len(tb) == 1 and tb[0] == ta[0]:
        return True
    return False
