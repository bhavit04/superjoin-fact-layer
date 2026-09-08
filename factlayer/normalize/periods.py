"""Turn the many ways a document names a time period into a comparable interval.

This module is the single biggest lever on reconciliation quality. Most apparent
contradictions in financial and macroeconomic documents are not disagreements at
all -- they are the same metric measured over different windows. You cannot tell
those apart until "FY24", "the year ended March 31, 2024", "Q4FY24" and "2023-24"
are all intervals on one timeline.

Convention note: these documents use the Indian fiscal year, April 1 -> March 31,
labelled by its *ending* calendar year. FY24 therefore runs 2023-04-01 to
2024-03-31, and its quarters are Q1 Apr-Jun, Q2 Jul-Sep, Q3 Oct-Dec, Q4 Jan-Mar.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

# The month a fiscal year starts in. April is the Indian convention and the
# default, but it is a property of the *document*, not of this system: a US filing
# means January-December by "FY2024" and would otherwise be silently shifted by a
# quarter. ``detect_fiscal_year_start`` reads it off the document instead.
FY_START_MONTH = 4  # April

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
}

ORDINAL_QUARTERS = {"first": 1, "second": 2, "third": 3, "fourth": 4}


@dataclass
class PeriodSpec:
    kind: str                 # FY | QUARTER | HALF | CY | MONTH | POINT | UNKNOWN
    start: str | None         # ISO date
    end: str | None           # ISO date
    label: str                # verbatim text we parsed
    canonical: str            # normalized label, e.g. "FY2024", "Q4 FY2024", "CY2024"
    is_point: bool = False    # a balance-sheet instant ("as at 31 March 2024")
    fiscal_ambiguous: bool = False  # a bare year that could be fiscal or calendar

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def known(self) -> bool:
        return self.start is not None and self.end is not None


# Set per document at ingest time by detect_fiscal_year_start().
_fy_start_month = FY_START_MONTH


def set_fiscal_year_start(month: int) -> None:
    """Set the fiscal-year start month used to resolve FY labels."""
    global _fy_start_month
    if 1 <= int(month) <= 12:
        _fy_start_month = int(month)


def get_fiscal_year_start() -> int:
    return _fy_start_month


# Phrases that reveal where a document's financial year ends. Whichever appears
# most often wins, so one stray mention does not flip the whole document.
_FY_END_PATTERNS = [
    (re.compile(r"year\s+end(?:ed|ing)\s+(?:on\s+)?(?:\d{1,2}\s+)?([A-Za-z]{3,9})", re.I), 1),
    (re.compile(r"(?:financial|fiscal)\s+year\s+end(?:s|ed|ing)?\s+(?:in\s+|on\s+)?([A-Za-z]{3,9})", re.I), 1),
    (re.compile(r"as\s+at\s+(?:\d{1,2}\s+)?([A-Za-z]{3,9})\s+\d{1,2},?\s*\d{4}", re.I), 1),
]


def detect_fiscal_year_start(text: str, default: int = FY_START_MONTH) -> int:
    """Infer a document's fiscal-year start month from how it names its year end.

    "the year ended March 31, 2024" implies a year starting in April; "year ended
    December 31, 2024" implies January. Without this, "FY2024" in a US or European
    filing is shifted by a quarter and every period comparison against it is
    quietly wrong.
    """
    from collections import Counter

    votes: Counter[int] = Counter()
    for pattern, group in _FY_END_PATTERNS:
        for match in pattern.finditer(text or ""):
            month = MONTHS.get(match.group(group).lower())
            if month:
                votes[month % 12 + 1] += 1   # the year starts the month after it ends
    if not votes:
        return default
    return votes.most_common(1)[0][0]


def _fy_bounds(end_year: int, start_month: int | None = None) -> tuple[date, date]:
    """FY labelled by its ending year -> (start, end)."""
    start_month = start_month or _fy_start_month
    if start_month == 1:                     # calendar-aligned fiscal year
        return date(end_year, 1, 1), date(end_year, 12, 31)
    end_month = start_month - 1
    return date(end_year - 1, start_month, 1), date(end_year, end_month, _last_day(end_year, end_month))


def _quarter_bounds(end_year: int, q: int, fy_start: int | None = None) -> tuple[date, date]:
    """Fiscal quarter within the FY labelled by ``end_year``."""
    fy_start = fy_start or _fy_start_month
    start_month = fy_start + 3 * (q - 1)
    start_year = (end_year if fy_start == 1 else end_year - 1) + (start_month - 1) // 12
    start_month = (start_month - 1) % 12 + 1
    end_month_abs = start_month + 2
    end_year_actual = start_year + (end_month_abs - 1) // 12
    end_month = (end_month_abs - 1) % 12 + 1
    last_day = _last_day(end_year_actual, end_month)
    return date(start_year, start_month, 1), date(end_year_actual, end_month, last_day)


def _last_day(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year + (month // 12), month % 12 + 1, 1) - __import__("datetime").timedelta(days=1)).day


def _expand_two_digit_year(token: str) -> int:
    n = int(token)
    if n < 100:
        return 2000 + n if n < 70 else 1900 + n
    return n


# --- Pattern table -----------------------------------------------------------
# Each entry is (compiled regex, handler). Handlers return a PeriodSpec or None.
# Order matters: the most specific patterns are tried first, so "Q4 FY24" is not
# consumed by the plain-FY pattern.

_P_QUARTER_FY = re.compile(r"\bQ([1-4])\s*[-/ ]?\s*FY\s*'?(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?\b", re.I)
_P_QUARTER_ORD = re.compile(
    r"\b(first|second|third|fourth)\s+quarter\s+(?:of\s+)?(?:FY|fiscal(?:\s+year)?)?\s*'?(\d{2,4})", re.I
)
_P_HALF_FY = re.compile(r"\bH([12])\s*[-/ ]?\s*FY\s*'?(\d{2,4})\b", re.I)
_P_NINE_MONTH = re.compile(r"\b9M\s*[-/ ]?\s*FY\s*'?(\d{2,4})\b", re.I)
_P_FY_RANGE = re.compile(r"\b(?:FY|fiscal(?:\s+year)?)\s*'?(\d{4})\s*[-–/]\s*(\d{2,4})\b", re.I)
_P_FY_SIMPLE = re.compile(r"\b(?:FY|fiscal(?:\s+year)?)\s*'?(\d{2,4})\b", re.I)
_P_YEAR_ENDED = re.compile(
    r"\b(?:for\s+the\s+)?(?:year|period|twelve\s+months)\s+end(?:ed|ing)\s+"
    r"(?:on\s+)?(\d{1,2})?\s*([A-Za-z]{3,9})\s*,?\s*(\d{1,2})?,?\s*(\d{4})", re.I
)
_P_AS_AT = re.compile(
    r"\b(?:as\s+(?:at|of|on)|balance\s+as\s+at)\s+(\d{1,2})?\s*([A-Za-z]{3,9})\s*,?\s*(\d{1,2})?,?\s*(\d{4})", re.I
)
_P_YEAR_RANGE = re.compile(r"\b(19|20)(\d{2})\s*[-–]\s*(\d{2})\b")
_P_CY = re.compile(r"\b(?:CY|calendar\s+year)\s*'?(\d{2,4})\b", re.I)
# "April to December 2024" is nine months, not December. Without this the range
# collapsed to its final month and a nine-month figure was compared against a
# one-month figure as though they covered the same period.
_P_MONTH_RANGE = re.compile(
    r"\b([A-Za-z]{3,9})\s*(?:to|through|[-–—])\s*([A-Za-z]{3,9})\s+(\d{4})\b", re.I
)
_P_MONTH_YEAR = re.compile(r"\b([A-Za-z]{3,9})\s+(\d{4})\b")
_P_BARE_YEAR = re.compile(r"\b(19\d{2}|20\d{2})\b")


def parse_period(text: str | None, fy_start: int | None = None) -> PeriodSpec:
    """Parse the first recognizable period expression in ``text``.

    ``fy_start`` is the document's fiscal-year start month, from
    ``detect_fiscal_year_start``. Passing it explicitly rather than reading a
    global keeps two documents with different conventions from interfering when
    they are ingested at the same time.
    """
    if not text:
        return PeriodSpec(kind="UNKNOWN", start=None, end=None, label="", canonical="")
    fy_start = fy_start or _fy_start_month
    raw = str(text).strip()

    if m := _P_QUARTER_FY.search(raw):
        q = int(m.group(1))
        year = _expand_two_digit_year(m.group(3) or m.group(2))
        if m.group(3) is None and len(m.group(2)) == 4:
            year = int(m.group(2))
        s, e = _quarter_bounds(year, q, fy_start)
        return PeriodSpec("QUARTER", s.isoformat(), e.isoformat(), m.group(0), f"Q{q} FY{year}")

    if m := _P_QUARTER_ORD.search(raw):
        q = ORDINAL_QUARTERS[m.group(1).lower()]
        year = _expand_two_digit_year(m.group(2))
        s, e = _quarter_bounds(year, q, fy_start)
        return PeriodSpec("QUARTER", s.isoformat(), e.isoformat(), m.group(0), f"Q{q} FY{year}")

    if m := _P_HALF_FY.search(raw):
        h = int(m.group(1))
        year = _expand_two_digit_year(m.group(2))
        s = _quarter_bounds(year, 1 if h == 1 else 3)[0]
        e = _quarter_bounds(year, 2 if h == 1 else 4)[1]
        return PeriodSpec("HALF", s.isoformat(), e.isoformat(), m.group(0), f"H{h} FY{year}")

    if m := _P_NINE_MONTH.search(raw):
        year = _expand_two_digit_year(m.group(1))
        s = _quarter_bounds(year, 1, fy_start)[0]
        e = _quarter_bounds(year, 3, fy_start)[1]
        return PeriodSpec("HALF", s.isoformat(), e.isoformat(), m.group(0), f"9M FY{year}")

    if m := _P_FY_RANGE.search(raw):
        # "FY 2023-24" -> the FY ending in 2024.
        second = m.group(2)
        year = _expand_two_digit_year(second) if len(second) == 2 else int(second)
        if len(second) == 2:
            year = int(m.group(1)[:2] + second) if int(second) >= int(m.group(1)[2:]) else int(m.group(1)) + 1
        s, e = _fy_bounds(year, fy_start)
        return PeriodSpec("FY", s.isoformat(), e.isoformat(), m.group(0), f"FY{year}")

    if m := _P_FY_SIMPLE.search(raw):
        year = _expand_two_digit_year(m.group(1))
        s, e = _fy_bounds(year, fy_start)
        return PeriodSpec("FY", s.isoformat(), e.isoformat(), m.group(0), f"FY{year}")

    if m := _P_YEAR_ENDED.search(raw):
        spec = _from_date_words(m, raw)
        if spec:
            month, day, year = spec
            end = date(year, month, day)
            start = date(year - 1, month, day) + __import__("datetime").timedelta(days=1)
            kind = "FY" if month == (fy_start - 1 or 12) else "CY"
            canonical = f"FY{year}" if kind == "FY" else f"12M to {end.isoformat()}"
            return PeriodSpec(kind, start.isoformat(), end.isoformat(), m.group(0), canonical)

    if m := _P_AS_AT.search(raw):
        spec = _from_date_words(m, raw)
        if spec:
            month, day, year = spec
            at = date(year, month, day)
            return PeriodSpec(
                "POINT", at.isoformat(), at.isoformat(), m.group(0),
                f"as at {at.isoformat()}", is_point=True,
            )

    if m := _P_CY.search(raw):
        year = _expand_two_digit_year(m.group(1))
        return PeriodSpec("CY", date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat(), m.group(0), f"CY{year}")

    if m := _P_YEAR_RANGE.search(raw):
        # "2023-24" in Indian macro writing is the fiscal year ending 2024.
        start_year = int(m.group(1) + m.group(2))
        end_year = int(m.group(1) + m.group(3)) if int(m.group(3)) >= int(m.group(2)) else start_year + 1
        if end_year - start_year == 1:
            s, e = _fy_bounds(end_year, fy_start)
            return PeriodSpec("FY", s.isoformat(), e.isoformat(), m.group(0), f"FY{end_year}")

    if m := _P_MONTH_RANGE.search(raw):
        first, last = MONTHS.get(m.group(1).lower()), MONTHS.get(m.group(2).lower())
        if first and last:
            year = int(m.group(3))
            start_year = year if last >= first else year - 1
            start = date(start_year, first, 1)
            end = date(year, last, _last_day(year, last))
            label = f"{start:%b %Y} – {end:%b %Y}"
            return PeriodSpec("RANGE", start.isoformat(), end.isoformat(), m.group(0), label)

    if m := _P_MONTH_YEAR.search(raw):
        month = MONTHS.get(m.group(1).lower())
        if month:
            year = int(m.group(2))
            s = date(year, month, 1)
            e = date(year, month, _last_day(year, month))
            return PeriodSpec("MONTH", s.isoformat(), e.isoformat(), m.group(0), f"{s:%b %Y}")

    if m := _P_BARE_YEAR.search(raw):
        year = int(m.group(1))
        return PeriodSpec(
            "CY", date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat(),
            m.group(0), f"{year}", fiscal_ambiguous=True,
        )

    return PeriodSpec(kind="UNKNOWN", start=None, end=None, label=raw[:80], canonical="")


def _from_date_words(m: re.Match, raw: str) -> tuple[int, int, int] | None:
    """Pull (month, day, year) out of a 'March 31, 2024' / '31 March 2024' match."""
    day_before, month_word, day_after, year = m.group(1), m.group(2), m.group(3), m.group(4)
    month = MONTHS.get(month_word.lower())
    if not month:
        return None
    day_token = day_before or day_after
    day = int(day_token) if day_token else _last_day(int(year), month)
    day = min(day, _last_day(int(year), month))
    return month, day, int(year)


# --- Interval comparison -----------------------------------------------------

EQUAL, CONTAINS, CONTAINED_BY, OVERLAPS, DISJOINT, UNKNOWN = (
    "EQUAL", "CONTAINS", "CONTAINED_BY", "OVERLAPS", "DISJOINT", "UNKNOWN"
)


def compare_periods(a: PeriodSpec, b: PeriodSpec) -> str:
    """How two periods sit relative to each other on the timeline."""
    if not a.known or not b.known:
        return UNKNOWN
    a_s, a_e, b_s, b_e = a.start, a.end, b.start, b.end
    if a_s == b_s and a_e == b_e:
        return EQUAL
    if a_s <= b_s and a_e >= b_e:
        return CONTAINS
    if b_s <= a_s and b_e >= a_e:
        return CONTAINED_BY
    if a_s > b_e or b_s > a_e:
        return DISJOINT
    return OVERLAPS


def describe_relation(rel: str, a: PeriodSpec, b: PeriodSpec) -> str:
    return {
        EQUAL: f"both cover {a.canonical or a.label}",
        CONTAINS: f"{a.canonical or a.label} contains {b.canonical or b.label}",
        CONTAINED_BY: f"{a.canonical or a.label} falls inside {b.canonical or b.label}",
        OVERLAPS: f"{a.canonical or a.label} partially overlaps {b.canonical or b.label}",
        DISJOINT: f"{a.canonical or a.label} and {b.canonical or b.label} do not overlap",
        UNKNOWN: "at least one period could not be resolved",
    }.get(rel, rel)
