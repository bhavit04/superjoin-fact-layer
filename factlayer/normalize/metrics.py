"""Canonicalize what is being measured.

"Revenue from operations" and "operating revenue" name one quantity; "revenue"
and "revenue growth" do not. Derivative metrics are flagged separately so a level
is never compared against its own growth rate.
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

# Ordered longest-first. The set matters more than it looks: metric labels are
# compared by their stemmed token sets, so "operations" and "operating" must
# reduce to the same stem or "revenue from operations" will not match "operating
# revenue", and "revenue"/"revenues" must agree or plural variants split apart.
_SUFFIXES = [
    "ational", "isation", "ization", "ations", "ating", "ation", "ates", "ate",
    "ings", "ing", "ences", "ence", "ances", "ance", "ments", "ment",
    "ives", "ive", "ies", "ers", "er", "es", "s",
]

_PUNCT = re.compile(r"[^\w\s%]")
_WS = re.compile(r"\s+")


def _stem(token: str) -> str:
    """Crude suffix stripping. Consistency matters more than correctness: every
    surface form must reach one stem or equal metrics are judged different."""
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    else:
        for suffix in _SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                token = token[: -len(suffix)]
                break
    if len(token) >= 5 and token.endswith("e"):
        token = token[:-1]
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


def same_quantity(label_a: str | None, label_b: str | None) -> bool:
    """Token sets must be equal, not merely similar.

    "net cash from OPERATING/INVESTING/FINANCING activities" share five of six
    tokens and score 0.67, yet are three unrelated line items — comparing them
    produced confident false contradictions. Synonyms whose words differ ("CPI
    inflation" / "consumer price inflation") are the clustering pass's job.
    """
    ta, tb = set(metric_tokens(label_a)), set(metric_tokens(label_b))
    return bool(ta) and ta == tb


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def metric_similarity(label_a: str | None, label_b: str | None) -> float:
    """0..1 similarity, blending token and character-trigram overlap. Used to
    rank candidates, never to authorise a comparison — see same_quantity."""
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
