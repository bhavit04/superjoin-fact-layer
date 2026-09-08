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
    """Crude but sufficient suffix stripping.

    Real stemming would be a heavyweight dependency for matching a few hundred
    metric labels. What matters is *consistency*: every surface form of a word
    must land on one stem, or two labels naming the same quantity will be judged
    different. The trailing-vowel strip at the end exists for exactly that --
    without it "revenue" and "revenues" reduce to different stems.
    """
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
    """Do two labels name the same measured quantity by their words alone?

    This is deliberately strict: the stemmed, stopword-stripped token sets must be
    equal. Similarity is not enough, because the labels that matter most here
    differ by exactly one word --

        net cash from (used in) OPERATING activities
        net cash from (used in) INVESTING activities
        net cash from (used in) FINANCING activities

    -- which share five of six tokens and score 0.67, yet are three unrelated line
    items. Comparing them produced confident, well-evidenced, completely false
    contradictions. The same applies to "EBITDA margin" against "Adj. EBITDA
    margin", where the one differing word is the whole point.

    Genuine synonyms whose words differ ("CPI inflation" / "consumer price
    inflation") are handled by the clustering pass instead, which asks a model.
    Missing a link costs a little recall; inventing a contradiction costs the
    system its credibility.
    """
    ta, tb = set(metric_tokens(label_a)), set(metric_tokens(label_b))
    return bool(ta) and ta == tb


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
