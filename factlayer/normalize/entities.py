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


def infer_primary_entity(
    subject_names: list[str], front_matter: str = "", title: str = ""
) -> str | None:
    """Guess the entity a document is *about*, to resolve its "the Company" references.

    Frequency alone is not enough, and gets this wrong in a characteristic way: in
    a segment-heavy earnings deck the most-mentioned subject is a business line
    ("Express Parcel"), not the company that owns it. Resolving "the Company" to a
    segment would then split one entity across documents and silently prevent any
    cross-document link from forming.

    So frequency is combined with where a name appears. A document names its own
    subject on the cover and in the opening pages, whereas segments and
    counterparties turn up later, in the body. Names carrying a legal suffix get a
    further nudge, because an organisation is a likelier document subject than a
    product line.
    """
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    had_suffix: dict[str, bool] = {}

    for raw in subject_names:
        if not raw or is_anaphoric(raw):
            continue
        key = normalize_entity(raw)
        if not key or len(key) < 3:
            continue
        counts[key] += 1
        tokens = _WS.sub(" ", _PUNCT.sub(" ", raw.lower())).split()
        if any(t in LEGAL_SUFFIXES for t in tokens):
            had_suffix[key] = True
        if key not in display or len(raw) > len(display[key]):
            display[key] = raw.strip()

    if not counts:
        return None

    front = _WS.sub(" ", _PUNCT.sub(" ", f"{title} {front_matter}".lower()))
    total = sum(counts.values()) or 1

    def score(key: str) -> float:
        # Frequency, but saturating: being mentioned 60 times rather than 30 does
        # not make something twice as likely to be the document's subject.
        value = (counts[key] / total) ** 0.5
        if front and key in front:
            value += 1.5              # named on the cover or in the opening pages
        if had_suffix.get(key):
            value += 0.4              # "... Limited" reads as an organisation
        value += 0.02 * min(len(key.split()), 4)
        return value

    best = max(counts, key=score)
    return display.get(best, best)


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
    # Exact equality only. Allowing a single-token subject to match any subject
    # beginning with it seemed harmless -- it was meant to join "india" to "indian
    # economy" -- but it also joined "WPI" to "WPI primary articles", so overall
    # wholesale inflation of 2.3 per cent was reported as contradicting the 5.1
    # per cent for one component of the same index. A component is not its whole,
    # which is the same principle the metric comparison already enforces.
    return key_a == key_b
