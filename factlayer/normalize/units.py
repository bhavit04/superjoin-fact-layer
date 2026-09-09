"""Parse a value as written into a comparable magnitude and unit.

`Rs. 8,142 Mn`, `INR 814.2 crore` and `81,420 lakh` are one quantity; comparison
only means anything once they collapse onto a common scale.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

# Multiplier words. Order matters only for the regex alternation below (longest first).
SCALES: dict[str, float] = {
    "trillion": 1e12, "trn": 1e12, "tn": 1e12,
    "billion": 1e9, "bn": 1e9,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
    "million": 1e6, "mn": 1e6, "mm": 1e6,
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5,
    "thousand": 1e3, "'000": 1e3, "k": 1e3,
    "hundred": 1e2,
}

CURRENCIES: list[tuple[str, str]] = [
    ("₹", "INR"), ("rs.", "INR"), ("rs", "INR"), ("inr", "INR"), ("rupee", "INR"), ("rupees", "INR"),
    ("us$", "USD"), ("usd", "USD"), ("$", "USD"), ("dollar", "USD"), ("dollars", "USD"),
    ("€", "EUR"), ("eur", "EUR"),
    ("£", "GBP"), ("gbp", "GBP"),
    ("¥", "JPY"), ("jpy", "JPY"),
]

# Unit tokens that are not currencies. Maps a surface form to a canonical unit tag.
PLAIN_UNITS: list[tuple[str, str]] = [
    ("percentage point", "pp"), ("percentage points", "pp"), ("ppt", "pp"),
    ("basis point", "bps"), ("basis points", "bps"), ("bps", "bps"), ("bp", "bps"),
    ("per cent", "%"), ("percent", "%"), ("%", "%"),
    ("times", "x"), ("x", "x"),
    ("years", "years"), ("year", "years"),
    ("months", "months"), ("month", "months"),
    ("days", "days"), ("day", "days"),
    ("metric tonnes", "tonnes"), ("tonnes", "tonnes"), ("tons", "tonnes"),
    ("sq ft", "sqft"), ("square feet", "sqft"), ("sq. ft.", "sqft"),
    ("bps.", "bps"),
]

_NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
# Letter boundaries, not word boundaries. "\b" fails on "76Cr" because there is
# no word boundary between a digit and a letter, so an attached scale suffix was
# silently dropped -- turning Rs 76 crore into Rs 76 and manufacturing a
# ten-million-fold discrepancy. Guarding on letters instead matches "76Cr",
# "₹8,142Cr" and "1.4 Mn" while still refusing the "cr" inside "increase".
_SCALE_RE = re.compile(
    r"(?<![a-zA-Z])(" + "|".join(sorted((re.escape(k) for k in SCALES), key=len, reverse=True)) + r")(?![a-zA-Z])",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE
)


@dataclass
class ValueSpec:
    """A document value, normalized enough that two of them can be compared."""

    kind: str                 # money | percent | ratio | count | duration | other
    number: float | None      # magnitude with the scale word already applied
    unit: str                 # canonical unit tag: INR, USD, %, pp, bps, x, count, days...
    raw: str                  # verbatim, as it appeared in the document
    scale: str | None = None  # the multiplier word we consumed, if any
    is_range: bool = False
    low: float | None = None
    high: float | None = None
    is_approximate: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def comparable(self) -> bool:
        return self.number is not None

    def display(self) -> str:
        return self.raw


def _to_float(token: str) -> float | None:
    """Handle both Western (1,234,567) and Indian (12,34,567) digit grouping."""
    cleaned = token.replace(",", "").replace("+", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _detect_currency(text: str) -> str | None:
    """Longest match wins, so `Rs.` beats a bare `s` and `US$` beats `$`."""
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for surface, code in CURRENCIES:
        idx = lowered.find(surface)
        if idx == -1:
            continue
        # Word-ish boundary check for alphabetic surfaces, so "rs" doesn't fire inside "years".
        if surface[0].isalpha():
            before = lowered[idx - 1] if idx > 0 else " "
            after_i = idx + len(surface)
            after = lowered[after_i] if after_i < len(lowered) else " "
            if before.isalpha() or (after.isalpha() and surface not in {"rs", "usd", "inr"}):
                continue
        if best is None or len(surface) > best[0]:
            best = (len(surface), code)
    return best[1] if best else None


def _detect_plain_unit(text: str) -> str | None:
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for surface, tag in PLAIN_UNITS:
        idx = lowered.find(surface)
        if idx == -1:
            continue
        if surface[0].isalpha():
            before = lowered[idx - 1] if idx > 0 else " "
            after_i = idx + len(surface)
            after = lowered[after_i] if after_i < len(lowered) else " "
            if before.isalpha() or after.isalpha():
                continue
        if best is None or len(surface) > best[0]:
            best = (len(surface), tag)
    return best[1] if best else None


def parse_value(raw: str, unit_hint: str | None = None) -> ValueSpec:
    """`unit_hint` carries a unit from a table header that the cell itself omits."""
    if raw is None:
        return ValueSpec(kind="other", number=None, unit="", raw="")
    text = str(raw).strip()
    if not text:
        return ValueSpec(kind="other", number=None, unit="", raw="")

    search_space = f"{text} {unit_hint or ''}"
    lowered = search_space.lower()

    is_approx = bool(re.search(r"\b(about|around|approx\.?|approximately|nearly|roughly|circa|~|over|almost)\b", lowered))

    matches = list(_NUM_RE.finditer(text))
    numbers = [_to_float(m.group()) for m in matches]
    numbers = [n for n in numbers if n is not None]

    # Accounting negative. The parentheses wrap the *number*, not necessarily the
    # whole string: "Rs. (452 Cr)" and "₹(452) Cr" are both minus 452 crore.
    # Requiring the entire string to be parenthesised missed both, turning a loss
    # into a profit and inventing a contradiction against the same figure written
    # elsewhere. Anchoring on the number also avoids reading a footnote marker
    # like "12.7%(2)" as a negative.
    negative_parens = False
    if matches:
        token = re.escape(matches[0].group())
        # A currency symbol commonly sits between the bracket and the digits --
        # "(₹8,911.39) million" -- and missing it flipped a loss to a profit, so
        # the same figure written "(8,911.39)" elsewhere came out 200% adrift.
        negative_parens = bool(
            re.search(r"\(\s*[^\d()]{0,8}" + token + r"\s*[^\d()]{0,12}\)", text)
        )

    scale_match = _SCALE_RE.search(search_space)
    scale_word = scale_match.group(1).lower() if scale_match else None
    multiplier = SCALES.get(scale_word, 1.0) if scale_word else 1.0

    currency = _detect_currency(search_space)
    plain_unit = _detect_plain_unit(search_space)

    # Decide the kind and canonical unit tag.
    if plain_unit in {"%", "pp", "bps"}:
        kind, unit = "percent", plain_unit
    elif currency:
        kind, unit = "money", currency
    elif plain_unit == "x":
        kind, unit = "ratio", "x"
    elif plain_unit in {"years", "months", "days"}:
        kind, unit = "duration", plain_unit
    elif plain_unit:
        kind, unit = "count", plain_unit
    elif numbers:
        kind, unit = "count", "count"
    else:
        kind, unit = "other", ""

    if not numbers:
        return ValueSpec(kind=kind, number=None, unit=unit, raw=text, is_approximate=is_approx)

    # A range is two numbers joined by a range separator: "6.3 to 6.8 per cent".
    # "2023-24" also matches that shape but is a fiscal year, not a range, so
    # year-like left operands with a two-digit right operand are rejected.
    is_range = False
    low = high = None
    range_match = _RANGE_RE.search(text)
    if range_match:
        left, right = _to_float(range_match.group(1)), _to_float(range_match.group(2))
        looks_like_fiscal_year = (
            left is not None and 1900 < left < 2100 and len(range_match.group(2).strip()) <= 2
        )
        if left is not None and right is not None and right > left and not looks_like_fiscal_year:
            is_range = True
            low, high = left * multiplier, right * multiplier

    value = numbers[0] * multiplier
    if is_range and low is not None and high is not None:
        value = (low + high) / 2.0
    if negative_parens and value > 0:
        value = -value
        if low is not None and high is not None:
            low, high = -high, -low

    return ValueSpec(
        kind=kind, number=value, unit=unit, raw=text, scale=scale_word,
        is_range=is_range, low=low, high=high, is_approximate=is_approx,
    )


# Units that mean the same thing once rescaled, so a fact in one can be compared to a
# fact in the other. Percentage points and percent are deliberately kept apart: a
# "2 pp increase" and a "2% level" are not the same claim.
CONVERSIONS: dict[tuple[str, str], float] = {
    ("bps", "%"): 0.01,
    ("%", "bps"): 100.0,
}


def to_common_unit(a: ValueSpec, b: ValueSpec) -> tuple[float, float, str] | None:
    """(a, b, unit) on a shared scale, or None. None is an answer, not a failure:
    INR against USD is a currency difference for the reconciler to explain."""
    if a.number is None or b.number is None:
        return None
    if a.unit == b.unit:
        return a.number, b.number, a.unit
    factor = CONVERSIONS.get((a.unit, b.unit))
    if factor is not None:
        return a.number * factor, b.number, b.unit
    factor = CONVERSIONS.get((b.unit, a.unit))
    if factor is not None:
        return a.number, b.number * factor, a.unit
    # An untagged count can be compared against a tagged count-like unit.
    if {a.unit, b.unit} & {"count", ""} and (a.kind == b.kind or "count" in (a.kind, b.kind)):
        other = a.unit if a.unit not in {"count", ""} else b.unit
        return a.number, b.number, other or "count"
    return None


def humanize(value: float | None, unit: str) -> str:
    """Render a magnitude the way a reader would write it."""
    if value is None:
        return "—"
    if unit in {"%", "pp", "bps", "x"}:
        return f"{value:,.2f}{'' if unit == 'x' else ''} {unit}".strip()
    magnitude = abs(value)
    # Currencies read naturally with the code in front ("INR 814.20 crore");
    # everything else reads better with the unit trailing ("1,517 tonnes").
    is_currency = unit in {"INR", "USD", "EUR", "GBP", "JPY"}
    if unit == "INR" and magnitude >= 1e7:
        return f"INR {value / 1e7:,.2f} crore"

    if magnitude >= 1e9:
        number = f"{value / 1e9:,.2f} bn"
    elif magnitude >= 1e6:
        number = f"{value / 1e6:,.2f} mn"
    elif magnitude >= 1e3:
        number = f"{value:,.0f}"
    else:
        number = f"{value:,.2f}"

    if not unit or unit == "count":
        return number
    return f"{unit} {number}" if is_currency else f"{number} {unit}"
