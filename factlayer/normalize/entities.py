"""Collapse surface forms of a subject onto one key.

Two problems: legal-suffix noise ("Delhivery Limited" / "Delhivery Ltd."), and
anaphora — filings say "the Company" far more often than they name themselves,
which would otherwise give every document its own useless entity.
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
    """Guess what a document is about, to resolve its "the Company" references.

    Frequency alone picked the segment "Express Parcel" (99 mentions) over
    "Delhivery Limited" (2) in an earnings deck, which would split one entity
    across documents. Names on the cover and opening pages are weighted heavily,
    since that is where a document names itself.
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
    """Exact match only.

    Letting a one-word subject match any subject starting with it joined "WPI" to
    "WPI primary articles", reporting overall inflation as contradicting one of
    its own components. A component is not its whole.
    """
    if not key_a or not key_b:
        return False
    return key_a == key_b
