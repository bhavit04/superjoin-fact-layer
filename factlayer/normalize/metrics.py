"""Canonicalize the *name* of what is being measured.

"Revenue from operations", "operating revenue", "revenues from operations" and
"total operating revenue" all name one quantity. Matching them by exact string
fails; matching them by embedding alone over-matches ("revenue" vs "revenue
growth" are different claims). The approach here is deliberately conservative:

- strip a small set of financial-writing stopwords and filler modifiers,
- apply light suffix stemming so operations/operating/operational collapse,
- keep a *token set*, which downstream similarity scores with Jaccard,
- and separately flag "derivative" metrics (growth, margin, share, per-unit),
  because a level and its growth rate must never be compared as the same claim.

That last point matters more than it looks: without it the system happily
reports that "revenue was Rs 8,142 Mn" contradicts "revenue grew 8.1 per cent".
"""
from __future__ import annotations

import re

STOPWORDS = {
    "the", "a", "an", "of", "for", "from", "in", "on", "at", "to", "and", "or",
    "as", "by", "with", "is", "was", "were", "be", "been", "its", "our", "their",
    "value", "amount", "figure", "number", "level", "during", "period", "year",
}

# Words that change *what kind of quantity* this is, not just its wording.
DERIVATIVE_MARKERS = {
    "growth": "growth", "grew": "growth", "increase": "growth", "rise": "growth",
    "decline": "growth", "yoy": "growth", "cagr": "growth", "change": "growth",
    "margin": "margin", "ratio": "ratio", "share": "share", "proportion": "share",
    "per": "per_unit", "average": "average", "median": "average",
    "forecast": "projection", "projected": "projection", "projection": "projection",
    "estimate": "projection", "target": "projection", "outlook": "projection",
}

_SUFFIXES = [
    "ational", "isation", "ization", "ations", "ation", "ings", "ing", "ences",
    "ence", "ances", "ance", "ments", "ment", "ives", "ive", "ies", "ers", "er",
    "es", "s",
]

_PUNCT = re.compile(r"[^\w\s%]")
_WS = re.compile(r"\s+")


def _stem(token: str) -> str:
    """Crude but sufficient suffix stripping. Real stemming is a dependency we
    do not need for matching a few hundred metric labels."""
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def metric_tokens(label: str | None) -> list[str]:
    if not label:
        return []
    text = _PUNCT.sub(" ", str(label).lower())
    text = _WS.sub(" ", text).strip()
    return [_stem(t) for t in text.split() if t and t not in STOPWORDS]


def metric_key(label: str | None) -> str:
    """A stable, order-independent key for a metric label."""
    tokens = metric_tokens(label)
    return " ".join(sorted(set(tokens)))


def derivative_kind(label: str | None) -> str | None:
    """Return 'growth' / 'margin' / 'share' / ... if the label names a derived
    quantity rather than a level, else None."""
    tokens = set(metric_tokens(label))
    raw_tokens = set(_WS.sub(" ", _PUNCT.sub(" ", str(label or "").lower())).split())
    for word, kind in DERIVATIVE_MARKERS.items():
        if word in raw_tokens or _stem(word) in tokens:
            return kind
    return None


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def metric_similarity(label_a: str | None, label_b: str | None) -> float:
    """0..1 similarity between two metric labels.

    Blends token overlap with character-trigram overlap so that both
    "revenue from operations"/"operating revenue" (token overlap) and
    "EBITDA"/"EBITDA margin" (character overlap) score sensibly.
    """
    ta, tb = set(metric_tokens(label_a)), set(metric_tokens(label_b))
    if not ta or not tb:
        return 0.0
    token_score = jaccard(ta, tb)
    ga, gb = _char_trigrams(" ".join(sorted(ta))), _char_trigrams(" ".join(sorted(tb)))
    char_score = jaccard(ga, gb)
    score = 0.65 * token_score + 0.35 * char_score
    # A level and a derived quantity are different claims however similar the words.
    if derivative_kind(label_a) != derivative_kind(label_b):
        score *= 0.45
    return round(score, 4)


def _char_trigrams(text: str) -> set[str]:
    padded = f"  {text}  "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}
