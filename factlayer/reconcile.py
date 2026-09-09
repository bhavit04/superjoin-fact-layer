"""Decide how two candidate facts relate.

    values disagree  !=  the sources contradict each other

Figures differ for good reasons — period, basis, scope, unit, vintage. Only when
no stated difference accounts for the gap is there a real conflict.

`observe` establishes what is mechanical (units reconciled, periods placed on a
timeline, ratio, differing qualifiers); `classify` applies deterministic rules and
settles roughly nine pairs in ten; only the rest reach a model, and they arrive
with the observations so it adjudicates rather than calculates.
"""
from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from dataclasses import dataclass, field, asdict
from typing import Any

from . import config
from .llm import LLMClient
from .pdf import normalize_ws
from .normalize import metrics, periods, units
from .prompts import ADJUDICATE_SYSTEM

CORROBORATES, CONTRADICTS, RECONCILED, RELATED, UNRELATED = (
    "CORROBORATES", "CONTRADICTS", "RECONCILED", "RELATED", "UNRELATED"
)

# Qualifier keys whose disagreement is a legitimate reason for values to differ.
# The value is the "dimension" label reported to the user.
EXPLANATORY_QUALIFIERS = {
    "basis": "basis", "consolidation": "basis", "accounting_basis": "basis",
    "scope": "scope", "segment": "scope", "business": "scope", "subsidiary": "scope",
    "product": "scope", "category": "scope", "entity": "scope", "coverage": "scope",
    "geography": "scope", "region": "scope", "country": "scope", "state": "scope",
    "measure": "definition", "measurement": "definition", "definition": "definition",
    "type": "definition", "metric_type": "definition", "valuation": "definition",
    "source": "vintage", "vintage": "vintage", "publication": "vintage",
    "restated": "vintage", "revision": "vintage", "status": "vintage",
    "estimate_type": "vintage", "projection": "vintage", "forecast": "vintage",
    "currency": "currency", "denomination": "currency",
}

# Ratios that betray a scale or unit mismatch rather than a disagreement. A list
# rather than a dict because several of these factors are numerically equal
# (crore/million is also just a factor of 10) and a dict would silently drop them.
SCALE_FACTORS: list[tuple[float, str]] = [
    (10, "a factor of 10, as between crore and million"),
    (100, "a factor of 100, as between crore and lakh"),
    (1000, "a factor of 1,000, as between thousands and units"),
    (1e5, "a factor of 100,000, as between lakh and units"),
    (1e6, "a factor of 1 million"),
    (1e7, "a factor of 10 million, as between crore and units"),
    (1e9, "a factor of 1 billion"),
]

_INTERNAL_QUALIFIERS = {"_period_source", "period", "period_label"}


@dataclass
class Observation:
    """Everything establishable about a pair without asking a model."""

    metric_similarity: float = 0.0
    same_cluster: bool = False
    same_document: bool = False
    derivative_match: bool = True

    units_a: str = ""
    units_b: str = ""
    both_numeric: bool = False
    units_comparable: bool = False
    value_a: float | None = None
    value_b: float | None = None
    ratio: float | None = None
    rel_diff: float | None = None
    tolerance: float = 0.01
    within_tolerance: bool | None = None
    range_contains: bool | None = None

    period_a: str = ""
    period_b: str = ""
    period_relation: str = periods.UNKNOWN
    period_note: str = ""

    weak_attribution: bool = False
    shared_evidence: bool = False
    sign_convention: bool = False
    text_a: str = ""
    text_b: str = ""
    text_equal: bool | None = None
    text_similarity: float | None = None
    kind_mismatch: bool = False

    qualifier_deltas: dict[str, list[str]] = field(default_factory=dict)
    hypotheses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Verdict:
    kind: str
    score: float
    method: str           # deterministic | llm | hybrid
    rationale: str
    dimension: str = ""
    needs_llm: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


# --- helpers -----------------------------------------------------------------

_WRITTEN_NUMBER = re.compile(r"\d[\d,]*(?:\.(\d+))?")


def _pct(value: float | None, places: int = 1) -> str:
    """Format a ratio as a percentage, tolerating an absent value.

    Rationales are user-facing strings assembled from optional observations; a
    missing number should read as "unknown", never take down the ingest."""
    if value is None:
        return "an unknown amount"
    return f"{value * 100:.{places}f}%"


def implied_tolerance(raw: str | None, value: float | None) -> float:
    """How much two figures may differ and still be the same number.

    Half a unit in the last stated decimal place, as a fraction of the printed
    number. "Rs 814 crore" resolves only to the nearest crore, so demanding it
    match "Rs. 8,142 Mn" to 0.01% would manufacture a contradiction out of
    rounding.
    """
    if value in (None, 0) or not raw:
        return 0.01
    match = _WRITTEN_NUMBER.search(str(raw))
    if not match:
        return 0.01
    printed = match.group(0).replace(",", "")
    try:
        magnitude = abs(float(printed))
    except ValueError:
        return 0.01
    if magnitude == 0:
        return 0.01
    decimals = len(match.group(1) or "")
    half_unit = 0.5 * (10 ** -decimals)
    return min(0.10, max(0.0005, half_unit / magnitude))


def _qualifier_dict(fact: dict) -> dict[str, str]:
    try:
        data = json.loads(fact.get("qualifiers_json") or "{}")
    except (TypeError, ValueError):
        return {}
    return {k: v for k, v in data.items() if k not in _INTERNAL_QUALIFIERS and isinstance(v, str)}


def _period_spec(fact: dict) -> periods.PeriodSpec:
    return periods.PeriodSpec(
        kind=fact.get("period_kind") or "UNKNOWN",
        start=fact.get("period_start"),
        end=fact.get("period_end"),
        label=fact.get("period_label") or "",
        canonical=fact.get("period_canonical") or "",
        is_point=bool(fact.get("period_is_point")),
    )


def _value_spec(fact: dict) -> units.ValueSpec:
    return units.ValueSpec(
        kind=fact.get("value_kind") or "other",
        number=fact.get("value_num"),
        unit=fact.get("value_unit") or "",
        raw=fact.get("value_raw") or "",
        is_range=bool(fact.get("is_range")),
        low=fact.get("value_low"),
        high=fact.get("value_high"),
        is_approximate=bool(fact.get("is_approximate")),
    )


_TEXT_NOISE = {"and", "the", "of", "a", "an", "&", "for", "to", "in", "at", "on", "with", "member"}


def _normalize_text_value(text: str | None) -> str:
    """Reduce a textual value to comparable words.

    Dropping connectives matters more than it sounds: "Managing Director and
    Chief Executive Officer" and "Managing Director & Chief Executive Officer"
    are one role, and comparing them literally reported the same person as
    contradicting themselves across two filings.
    """
    words = re.sub(r"[^\w]+", " ", str(text or "").replace("&", " and ").lower()).split()
    return " ".join(w for w in words if w not in _TEXT_NOISE)


def _scale_hypothesis(ratio: float) -> str | None:
    for factor, label in SCALE_FACTORS:
        for candidate in (factor, 1.0 / factor):
            if candidate and abs(ratio / candidate - 1.0) < 0.02:
                return label
    # A looser check for the common case where a scale mismatch is compounded by
    # rounding: "1,517" in thousands against "1.4 Mn Tons" is 1/923, not a clean
    # 1/1000, but two figures for one metric and period differing by roughly a
    # power of ten are a units problem, not a factual disagreement.
    magnitude = abs(ratio)
    if magnitude > 0:
        exponent = round(math.log10(magnitude))
        if exponent != 0 and abs(magnitude / (10.0 ** exponent) - 1.0) < config.THRESHOLDS.scale_window:
            return f"approximately a factor of 10^{exponent}, suggesting a scale or unit mismatch"
    return None


# --- stage 1: mechanical observation -----------------------------------------

def observe(fact_a: dict, fact_b: dict, similarity: float, same_cluster: bool) -> Observation:
    obs = Observation(
        metric_similarity=round(similarity, 4),
        same_cluster=same_cluster,
        same_document=fact_a.get("doc_id") == fact_b.get("doc_id"),
        derivative_match=(fact_a.get("derivative_kind") or None) == (fact_b.get("derivative_kind") or None),
    )

    period_a, period_b = _period_spec(fact_a), _period_spec(fact_b)
    obs.period_a = period_a.canonical or period_a.label
    obs.period_b = period_b.canonical or period_b.label
    obs.period_relation = periods.compare_periods(period_a, period_b)
    obs.period_note = periods.describe_relation(obs.period_relation, period_a, period_b)

    value_a, value_b = _value_spec(fact_a), _value_spec(fact_b)
    obs.units_a, obs.units_b = value_a.unit, value_b.unit
    obs.both_numeric = value_a.number is not None and value_b.number is not None
    # One side a quantity and the other a name or status means the metric label was
    # shared but the claims are not: "number of members = 3" against "member =
    # Suvir Suren Sujan" is not a disagreement about the same thing.
    obs.kind_mismatch = (value_a.number is None) != (value_b.number is None)

    # Two facts quoting one span are two readings of a statement, not two sources:
    # "reduced ... from 38 to 31" yields both numbers and would self-contradict.
    ev_a = normalize_ws(fact_a.get("evidence_text") or "").lower()
    ev_b = normalize_ws(fact_b.get("evidence_text") or "").lower()
    if ev_a and ev_b and fact_a.get("doc_id") == fact_b.get("doc_id"):
        obs.shared_evidence = (
            ev_a == ev_b
            or (len(ev_a) > 40 and len(ev_b) > 40 and (ev_a in ev_b or ev_b in ev_a))
            or SequenceMatcher(None, ev_a[:220], ev_b[:220], autojunk=False).ratio()
            >= config.THRESHOLDS.shared_evidence
        )
    # Evidence that never says what it measures cannot support a conflict.
    obs.weak_attribution = min(
        float(fact_a.get("metric_support") if fact_a.get("metric_support") is not None else 1.0),
        float(fact_b.get("metric_support") if fact_b.get("metric_support") is not None else 1.0),
    ) < config.THRESHOLDS.attribution_floor

    common = units.to_common_unit(value_a, value_b)
    if common:
        obs.units_comparable = True
        a_val, b_val, _unit = common
        obs.value_a, obs.value_b = a_val, b_val
        scale = max(abs(a_val), abs(b_val))
        if scale > 0:
            obs.rel_diff = abs(a_val - b_val) / scale
            if b_val != 0:
                obs.ratio = a_val / b_val
        else:
            # Both figures are zero, which is agreement, not an undefined
            # comparison. Leaving rel_diff unset here crashed every rationale
            # that formats it as a percentage.
            obs.rel_diff = 0.0
            obs.ratio = 1.0
        obs.tolerance = max(
            implied_tolerance(value_a.raw, a_val), implied_tolerance(value_b.raw, b_val)
        )
        if value_a.is_approximate or value_b.is_approximate:
            obs.tolerance = max(obs.tolerance, 0.05)
        if obs.rel_diff is not None:
            obs.within_tolerance = obs.rel_diff <= obs.tolerance

        # Equal magnitude, opposite sign: a loss in accounting brackets and the
        # same loss described in prose is one figure under two conventions.
        if a_val and b_val and a_val * b_val < 0:
            magnitude_gap = abs(abs(a_val) - abs(b_val)) / max(abs(a_val), abs(b_val))
            obs.sign_convention = magnitude_gap <= max(obs.tolerance, 0.01)

        # A stated range that brackets the other figure is agreement, not conflict.
        for ranged, point in ((value_a, b_val), (value_b, a_val)):
            if ranged.is_range and ranged.low is not None and ranged.high is not None:
                if ranged.low - 1e-9 <= point <= ranged.high + 1e-9:
                    obs.range_contains = True
        if obs.range_contains is None and (value_a.is_range or value_b.is_range):
            obs.range_contains = False
    else:
        obs.text_a = _normalize_text_value(fact_a.get("value_raw"))
        obs.text_b = _normalize_text_value(fact_b.get("value_raw"))
        if obs.text_a and obs.text_b:
            # "Chairperson & Non-Executive Independent Director" and "Chairman and
            # Non-Executive Independent Director" are one role. Exact matching, even
            # after dropping connectives, reported the same person as contradicting
            # themselves across two filings, so near-identical wording counts as
            # equal.
            ratio = SequenceMatcher(None, obs.text_a, obs.text_b, autojunk=False).ratio()
            obs.text_similarity = round(ratio, 3)
            obs.text_equal = (
                obs.text_a == obs.text_b
                or obs.text_a in obs.text_b
                or obs.text_b in obs.text_a
                or ratio >= config.THRESHOLDS.text_equality
            )

    # Which stated conditions differ?
    qa, qb = _qualifier_dict(fact_a), _qualifier_dict(fact_b)
    for key in set(qa) | set(qb):
        left, right = qa.get(key, ""), qb.get(key, "")
        if _normalize_text_value(left) != _normalize_text_value(right):
            obs.qualifier_deltas[key] = [left, right]

    # Hypotheses: mechanical explanations for any gap, offered to the adjudicator.
    if obs.ratio and obs.within_tolerance is False:
        scale = _scale_hypothesis(abs(obs.ratio))
        if scale:
            obs.hypotheses.append(f"values differ by {scale}, suggesting a unit or scale mismatch")
        if 60 <= abs(obs.ratio) <= 100 or 0.01 <= abs(obs.ratio) <= 1 / 60:
            obs.hypotheses.append(
                "the ratio is close to a plausible INR/USD exchange rate, suggesting a currency difference"
            )
    if obs.units_comparable is False and obs.units_a and obs.units_b:
        obs.hypotheses.append(f"values are stated in different units ({obs.units_a} vs {obs.units_b})")
    if obs.period_relation in (periods.CONTAINS, periods.CONTAINED_BY):
        obs.hypotheses.append(f"periods nest: {obs.period_note}")
    if obs.period_relation == periods.DISJOINT:
        obs.hypotheses.append(f"periods do not overlap: {obs.period_note}")
    for key, (left, right) in obs.qualifier_deltas.items():
        dimension = EXPLANATORY_QUALIFIERS.get(key)
        if dimension:
            obs.hypotheses.append(
                f"stated {key} differs ({left or 'unstated'} vs {right or 'unstated'}), a {dimension} difference"
            )
    return obs


# --- stage 2: deterministic classification -----------------------------------

def classify(fact_a: dict, fact_b: dict, obs: Observation) -> Verdict:
    """Settle the pair from the observations alone, or mark it for adjudication."""
    if obs.sign_convention:
        return Verdict(
            RECONCILED, 0.7, "deterministic",
            f"The two figures have the same magnitude but opposite signs "
            f"({units.humanize(obs.value_a, obs.units_a)} and {units.humanize(obs.value_b, obs.units_b)}). "
            "One source states the amount in accounting notation and the other describes it in "
            "prose, so this is a sign convention rather than a disagreement.",
            dimension="sign convention",
        )

    if obs.shared_evidence:
        return Verdict(
            RELATED, 0.3, "deterministic",
            "Both facts were read from the same span of text, so they are two values drawn from "
            "one statement -- such as a change from one figure to another, or two columns of a "
            "single table row -- rather than two sources making competing claims.",
            dimension="same evidence",
        )

    if not obs.derivative_match:
        return Verdict(
            RELATED, 0.3, "deterministic",
            "One fact is a level and the other a derived quantity (growth, margin, share), "
            "so they are not the same claim.",
        )

    explanatory = {
        EXPLANATORY_QUALIFIERS[k] for k in obs.qualifier_deltas if k in EXPLANATORY_QUALIFIERS
    }
    # An allowlist would defeat the open qualifier design: "partner: ACT grants"
    # vs "partner: Hunger Heroes" are two programmes, and that key is not on any
    # list. Any stated difference counts as a candidate explanation.
    unrecognized = [k for k in obs.qualifier_deltas if k not in EXPLANATORY_QUALIFIERS]

    # --- non-numeric facts ---------------------------------------------------
    if obs.kind_mismatch:
        return Verdict(
            RELATED, 0.25, "deterministic",
            "One source states a quantity here and the other states a name or a status, so "
            "these describe different things despite sharing a metric label.",
            dimension="definition",
        )
    if not obs.both_numeric:
        if obs.text_equal is True:
            return Verdict(
                CORROBORATES, 0.8, "deterministic",
                f"Both sources state the same value for this claim: \"{fact_a.get('value_raw')}\".",
            )
        # Time applies to textual claims too. A value stated for one period and a
        # different value stated for a later, non-overlapping period is a change
        # over time -- a director appointed and later resigned, a line item that
        # was nil and later was not -- and calling that a contradiction misreads
        # the most ordinary thing documents do.
        if obs.period_relation == periods.DISJOINT:
            return Verdict(
                RELATED, 0.4, "deterministic",
                f"The value differs between two non-overlapping periods ({obs.period_a} vs "
                f"{obs.period_b}), which describes a change over time rather than a conflict.",
                dimension="period",
            )
        if obs.text_equal is False:
            # Differing statuses over time are a change, not a conflict, so this
            # always goes to the adjudicator with the timeline attached.
            return Verdict(
                CONTRADICTS, 0.4, "deterministic",
                "The two sources state different values for the same claim.",
                needs_llm=True,
            )
        return Verdict(RELATED, 0.25, "deterministic", "Values could not be compared mechanically.", needs_llm=True)

    # --- numeric, but the units cannot be put on one scale ---------------------
    # Two money figures in different currencies are the clearest case: they are not
    # in conflict, they are denominated differently, and only the exchange rate
    # implied by the pair can say whether they agree.
    if not obs.units_comparable:
        currencies = {"INR", "USD", "EUR", "GBP", "JPY"}
        is_currency_gap = obs.units_a in currencies and obs.units_b in currencies
        return Verdict(
            RECONCILED, 0.5, "deterministic",
            (f"The figures are denominated in different currencies ({obs.units_a} vs {obs.units_b}), "
             "so they are not directly comparable without an exchange rate."
             if is_currency_gap else
             f"The figures are stated in different units ({obs.units_a} vs {obs.units_b}), "
             "so they are not directly comparable."),
            dimension="currency" if is_currency_gap else "unit", needs_llm=True,
        )

    period_rel = obs.period_relation

    # --- same period ---------------------------------------------------------
    if period_rel == periods.EQUAL:
        if obs.within_tolerance or obs.range_contains:
            detail = (
                f"Both resolve to {units.humanize(obs.value_a, obs.units_a)} for {obs.period_a}"
                if obs.rel_diff is not None and obs.rel_diff < 1e-9
                else (
                    f"{units.humanize(obs.value_a, obs.units_a)} and "
                    f"{units.humanize(obs.value_b, obs.units_b)} agree to within "
                    f"{_pct(obs.rel_diff, 2)} for {obs.period_a}, inside the {_pct(obs.tolerance, 2)} "
                    f"tolerance implied by how precisely each figure is written"
                )
            )
            return Verdict(CORROBORATES, min(0.99, 0.75 + 0.24 * obs.metric_similarity), "deterministic", detail + ".")
        if explanatory:
            dimension = sorted(explanatory)[0]
            return Verdict(
                RECONCILED, 0.6, "deterministic",
                f"The figures differ by {_pct(obs.rel_diff)} for the same period, but the sources "
                f"state a different {dimension}, which would account for it.",
                dimension=dimension, needs_llm=True,
            )
        if obs.hypotheses:
            # When the ratio is itself the explanation this is arithmetic, and
            # escalating invited the model to overturn a correct reconciliation.
            scale_explained = any("factor of 10" in h or "scale" in h for h in obs.hypotheses)
            return Verdict(
                RECONCILED, 0.6 if scale_explained else 0.55, "deterministic",
                f"The figures differ by {_pct(obs.rel_diff)} for {obs.period_a}; "
                f"{obs.hypotheses[0]}.",
                dimension="unit", needs_llm=not scale_explained,
            )
        if obs.weak_attribution:
            return Verdict(
                RELATED, 0.3, "deterministic",
                "The figures differ, but at least one source's evidence does not say what its "
                "number measures -- the metric was inferred from surrounding context. There is "
                "not enough here to claim the two describe the same quantity.",
                dimension="attribution",
            )
        if unrecognized:
            key = sorted(unrecognized)[0]
            left, right = obs.qualifier_deltas[key]
            return Verdict(
                RECONCILED, 0.5, "deterministic",
                f"The figures differ by {_pct(obs.rel_diff)}, but the sources state a different "
                f"{key.replace('_', ' ')} ({left or 'unstated'} vs {right or 'unstated'}), which "
                "would account for it.",
                dimension=key.replace("_", " "), needs_llm=True,
            )
        return Verdict(
            CONTRADICTS, 0.65, "deterministic",
            f"Both sources report this metric for {obs.period_a}, with no stated difference in "
            f"basis, scope or units, yet the figures differ by {_pct(obs.rel_diff)} "
            f"({units.humanize(obs.value_a, obs.units_a)} vs {units.humanize(obs.value_b, obs.units_b)}).",
            needs_llm=True,
        )

    # --- nested periods ------------------------------------------------------
    if period_rel in (periods.CONTAINS, periods.CONTAINED_BY):
        bigger, smaller = (
            (obs.value_a, obs.value_b) if period_rel == periods.CONTAINS else (obs.value_b, obs.value_a)
        )
        # A part exceeding its whole is only impossible for a non-negative
        # quantity. EBITDA goes negative, so a profitable quarter inside a
        # loss-making year is ordinary — raise it, do not assert it.
        additive = obs.units_a not in {"%", "pp", "bps", "x"} and not metrics.derivative_kind(
            fact_a.get("metric_raw")
        )
        exceeds = (
            additive and smaller is not None and bigger is not None and smaller > bigger * 1.02
        )
        if exceeds:
            obs.hypotheses.insert(0, (
                f"the shorter period reports {units.humanize(smaller, obs.units_a)}, which exceeds "
                f"the {units.humanize(bigger, obs.units_a)} reported for the longer period "
                "containing it -- consistent only if other sub-periods were negative"
            ))
            return Verdict(
                RECONCILED, 0.45, "deterministic",
                f"These cover nested periods ({obs.period_note}), but the shorter period's figure "
                f"exceeds the longer one's. That is possible for a measure that can go negative, "
                f"such as profit or EBITDA, and an inconsistency otherwise.",
                dimension="period", needs_llm=True,
            )
        return Verdict(
            RECONCILED, 0.7, "deterministic",
            f"These are the same metric over nested periods: {obs.period_note}. The difference is "
            "one of reporting window, not a disagreement.",
            dimension="period",
        )

    # --- non-overlapping periods --------------------------------------------
    if period_rel == periods.DISJOINT:
        return Verdict(
            RELATED, 0.45, "deterministic",
            f"Same metric measured over different, non-overlapping periods ({obs.period_a} vs "
            f"{obs.period_b}). This is a time series, not a conflict.",
            dimension="period",
        )

    if period_rel == periods.OVERLAPS:
        return Verdict(
            RECONCILED, 0.5, "deterministic",
            f"The reporting windows only partially overlap: {obs.period_note}.",
            dimension="period", needs_llm=True,
        )

    # --- period unknown on at least one side ---------------------------------
    if obs.within_tolerance:
        return Verdict(
            CORROBORATES, 0.62, "deterministic",
            f"The figures agree to within {_pct(obs.rel_diff, 2)}, though at least one source does not "
            "state a period that could be resolved.",
            needs_llm=False,
        )
    return Verdict(
        RELATED, 0.35, "deterministic",
        "The same metric is reported with different values, but at least one period could not be "
        "resolved, so they cannot be compared with confidence.",
        needs_llm=True,
    )


# --- enumerations are not disagreements --------------------------------------

# Kept as a name for readability; the live value comes from config.THRESHOLDS.
ENUMERATION_MIN_VALUES = 3


def find_enumerations(facts: list[dict]) -> set[tuple]:
    """Group keys whose facts are a list of events, not one claim.

    A share-capital history repeats "equity shares allotted" for 2023 with a
    different value per allotment; pairwise those read as contradictions though
    nothing conflicts. Three or more distinct values for one subject, metric and
    period within a document is an enumeration. The threshold is three because
    two rival values is exactly the case worth keeping.
    """
    groups: dict[tuple, set[float]] = {}
    for fact in facts:
        if fact.get("value_num") is None:
            continue
        key = (
            fact.get("doc_id"), fact.get("subject_key"),
            fact.get("metric_cluster"), fact.get("period_canonical") or "",
        )
        groups.setdefault(key, set()).add(round(float(fact["value_num"]), 6))
    floor = config.THRESHOLDS.enumeration_min
    return {key for key, values in groups.items() if len(values) >= floor}


def enumeration_key(fact: dict) -> tuple:
    return (
        fact.get("doc_id"), fact.get("subject_key"),
        fact.get("metric_cluster"), fact.get("period_canonical") or "",
    )


# --- stage 3: LLM adjudication -----------------------------------------------

def _fact_brief(fact: dict, label: str, doc_title: str) -> str:
    qualifiers = _qualifier_dict(fact)
    lines = [
        f"{label}:",
        f"  document: {doc_title}  (page {fact.get('page')})",
        f"  subject: {fact.get('subject_raw')}",
        f"  metric: {fact.get('metric_raw')}",
        f"  value as printed: {fact.get('value_raw')}",
    ]
    if fact.get("value_num") is not None:
        lines.append(f"  normalized value: {units.humanize(fact['value_num'], fact.get('value_unit') or '')}")
    if fact.get("period_canonical") or fact.get("period_label"):
        lines.append(f"  period: {fact.get('period_label')}  (resolved: {fact.get('period_canonical') or 'unresolved'})")
    if qualifiers:
        rendered = "; ".join(f"{k}={v}" for k, v in sorted(qualifiers.items()))
        lines.append(f"  stated qualifiers: {rendered}")
    lines.append(f'  source evidence: "{fact.get("evidence_text")}"')
    return "\n".join(lines)


def build_adjudication_prompt(
    fact_a: dict, fact_b: dict, obs: Observation, prior: Verdict, titles: dict[str, str]
) -> str:
    observations = [
        f"- metric label similarity: {obs.metric_similarity}",
        f"- period relationship: {obs.period_relation} ({obs.period_note})",
    ]
    if obs.units_comparable:
        observations.append(
            f"- units reconciled onto {obs.units_a}: Fact A = {obs.value_a:,.4g}, Fact B = {obs.value_b:,.4g}"
        )
        if obs.rel_diff is not None:
            observations.append(
                f"- relative difference: {obs.rel_diff:.4%} against a rounding tolerance of {obs.tolerance:.4%}"
                f" -> {'within' if obs.within_tolerance else 'outside'} tolerance"
            )
        if obs.ratio is not None:
            observations.append(f"- ratio A/B: {obs.ratio:.6g}")
    else:
        observations.append(f"- units are NOT directly comparable: {obs.units_a!r} vs {obs.units_b!r}")
    if obs.range_contains is not None:
        observations.append(f"- one value is a range and it {'does' if obs.range_contains else 'does not'} contain the other")
    if obs.qualifier_deltas:
        for key, (left, right) in sorted(obs.qualifier_deltas.items()):
            observations.append(f"- qualifier {key!r} differs: A={left or '(unstated)'!r} B={right or '(unstated)'!r}")
    else:
        observations.append("- the two facts state no conflicting qualifiers")
    if obs.weak_attribution:
        observations.append(
            "- WARNING: at least one evidence quote does not state what its number measures, so "
            "the metric was inferred from surrounding context. Do not call this a contradiction "
            "unless both quotes independently establish they measure the same quantity."
        )
    for hypothesis in obs.hypotheses:
        observations.append(f"- possible explanation: {hypothesis}")
    observations.append(f"- both facts come from {'the same document' if obs.same_document else 'different documents'}")

    return (
        f"{_fact_brief(fact_a, 'Fact A', titles.get(fact_a.get('doc_id'), 'unknown document'))}\n\n"
        f"{_fact_brief(fact_b, 'Fact B', titles.get(fact_b.get('doc_id'), 'unknown document'))}\n\n"
        f"Mechanical observations already computed (trust these over your own arithmetic):\n"
        + "\n".join(observations)
        + f"\n\nThe rule-based pass provisionally called this {prior.kind}, reasoning: {prior.rationale}\n"
        "Confirm or overturn it, and explain the relationship for a reader who can see both "
        "pieces of evidence above. Return only the JSON object."
    )


async def adjudicate(
    client: LLMClient,
    fact_a: dict,
    fact_b: dict,
    obs: Observation,
    prior: Verdict,
    titles: dict[str, str],
) -> Verdict:
    """Ask a model to confirm or overturn the rule-based verdict."""
    payload = await client.complete_json(
        system=ADJUDICATE_SYSTEM,
        prompt=build_adjudication_prompt(fact_a, fact_b, obs, prior, titles),
        task="adjudicate_pair",
        max_output_tokens=1024,
        default={},
    )
    if not isinstance(payload, dict) or not payload.get("verdict"):
        # No model answer available: keep the deterministic call and say so.
        prior.detail["adjudicated"] = False
        return prior

    kind = str(payload.get("verdict", "")).upper().strip()
    if kind not in {CORROBORATES, CONTRADICTS, RECONCILED, RELATED, UNRELATED}:
        prior.detail["adjudicated"] = False
        return prior

    try:
        confidence = float(payload.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    explanation = str(payload.get("explanation") or "").strip()
    quote = str(payload.get("reconciling_evidence") or "").strip()
    dimension = str(payload.get("dimension") or "").strip().lower() or prior.dimension

    rationale = explanation or prior.rationale
    if quote:
        rationale = f"{rationale} Supporting words: “{quote[:220]}”"

    return Verdict(
        kind=kind,
        score=round(min(1.0, max(0.0, confidence)), 3),
        method="hybrid" if kind == prior.kind else "llm",
        rationale=rationale,
        dimension=dimension,
        detail={
            "adjudicated": True,
            "rule_verdict": prior.kind,
            "rule_rationale": prior.rationale,
            "overturned": kind != prior.kind,
            "model_quote": quote[:400],
        },
    )
