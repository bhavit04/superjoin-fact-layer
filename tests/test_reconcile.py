"""The decision table, tested directly.

These assertions are the four cases the assignment asks for, expressed as unit
tests over synthetic facts. They run with no API key and no PDFs, which is the
point: the distinction between "the values differ" and "the sources contradict
each other" is deterministic and inspectable, not something an LLM is trusted to
get right on its own.
"""
from conftest import make_fact

from factlayer.reconcile import (
    CONTRADICTS, CORROBORATES, RECONCILED, RELATED, classify, observe,
)


def decide(a, b, similarity=1.0, same_cluster=True):
    obs = observe(a, b, similarity, same_cluster)
    return classify(a, b, obs), obs


# --- case 1: corroboration despite different wording -------------------------

def test_same_quantity_written_three_ways_corroborates():
    """Rs 8,142 Mn in one document, Rs 814 crore in another, one stated as
    'FY24' and the other as 'the year ended March 31, 2024'."""
    a = make_fact(id="a", value_raw="8,142", value_num=8_142_000_000.0)
    b = make_fact(
        id="b", doc_id="doc_b", value_raw="814", value_num=8_140_000_000.0,
        metric_raw="operating revenue", period_label="the year ended March 31, 2024",
    )
    verdict, obs = decide(a, b)
    assert verdict.kind == CORROBORATES
    assert verdict.method == "deterministic"
    assert obs.period_relation == "EQUAL"
    # The gap is real but smaller than the precision at which "814" was written.
    assert 0 < obs.rel_diff <= obs.tolerance


def test_rounding_is_not_a_contradiction():
    a = make_fact(id="a", value_raw="8.1", value_num=8_100_000_000.0)
    b = make_fact(id="b", doc_id="doc_b", value_raw="8,142", value_num=8_142_000_000.0)
    assert decide(a, b)[0].kind == CORROBORATES


def test_a_stated_range_containing_the_other_figure_corroborates():
    forecast = make_fact(
        id="a", metric_raw="real gdp growth", metric_key="gdp growth real",
        metric_cluster="gdp growth real", derivative_kind="growth",
        value_raw="6.3 to 6.8 per cent", value_num=6.55, value_low=6.3, value_high=6.8,
        value_unit="%", value_kind="percent", is_range=1,
    )
    actual = make_fact(
        id="b", doc_id="doc_b", metric_raw="real gdp growth", metric_key="gdp growth real",
        metric_cluster="gdp growth real", derivative_kind="growth",
        value_raw="6.5 per cent", value_num=6.5, value_unit="%", value_kind="percent",
    )
    assert decide(forecast, actual)[0].kind == CORROBORATES


# --- case 2: a genuine contradiction -----------------------------------------

def test_same_metric_same_period_no_explanation_contradicts():
    a = make_fact(id="a", value_raw="8,142", value_num=8_142_000_000.0)
    b = make_fact(id="b", doc_id="doc_b", value_raw="9,010", value_num=9_010_000_000.0)
    verdict, obs = decide(a, b)
    assert verdict.kind == CONTRADICTS
    assert verdict.needs_llm is True          # escalated for confirmation
    assert not obs.qualifier_deltas           # nothing stated explains the gap


def test_a_part_larger_than_its_whole_is_escalated_not_asserted():
    """A quarter reporting more than the year containing it looks impossible, and
    for a non-negative quantity it is. But EBITDA and profit go negative -- a
    profitable quarter inside a loss-making year is ordinary -- so this layer
    raises the tension as a hypothesis rather than asserting an impossibility it
    cannot establish."""
    year = make_fact(id="a", value_raw="8,142", value_num=8_142_000_000.0)
    quarter = make_fact(
        id="b", doc_id="doc_b", value_raw="9,500", value_num=9_500_000_000.0,
        period_label="Q4 FY24", period_canonical="Q4 FY2024", period_kind="QUARTER",
        period_start="2024-01-01", period_end="2024-03-31",
    )
    verdict, obs = decide(year, quarter)
    assert verdict.kind == RECONCILED
    assert verdict.needs_llm is True
    assert any("exceeds" in h for h in obs.hypotheses)


# --- case 3: apparent contradiction explained by context ---------------------

def test_nested_periods_are_reconciled_not_contradicted():
    year = make_fact(id="a", value_raw="8,142", value_num=8_142_000_000.0)
    quarter = make_fact(
        id="b", doc_id="doc_b", value_raw="2,194", value_num=2_194_000_000.0,
        period_label="Q4FY24", period_canonical="Q4 FY2024", period_kind="QUARTER",
        period_start="2024-01-01", period_end="2024-03-31",
    )
    verdict, _ = decide(year, quarter)
    assert verdict.kind == RECONCILED
    assert verdict.dimension == "period"
    assert verdict.needs_llm is False         # the rules alone are sufficient here


def test_consolidated_versus_standalone_is_reconciled_on_basis():
    a = make_fact(id="a", value_num=8_142_000_000.0, qualifiers={"basis": "consolidated"})
    b = make_fact(id="b", doc_id="doc_b", value_raw="7,300", value_num=7_300_000_000.0,
                  qualifiers={"basis": "standalone"})
    verdict, obs = decide(a, b)
    assert verdict.kind == RECONCILED
    assert verdict.dimension == "basis"
    assert "basis" in obs.qualifier_deltas


def test_a_factor_of_ten_reads_as_a_scale_mismatch():
    a = make_fact(id="a", value_raw="8,142", value_num=8_142_000_000.0)
    b = make_fact(id="b", doc_id="doc_b", value_raw="814.2", value_num=814_200_000.0)
    verdict, obs = decide(a, b)
    assert verdict.kind == RECONCILED
    assert any("factor of 10" in h for h in obs.hypotheses)


def test_different_currencies_are_reconciled_not_contradicted():
    inr = make_fact(id="a", value_num=8_142_000_000.0, value_unit="INR")
    usd = make_fact(id="b", doc_id="doc_b", value_raw="$97.4 million",
                    value_num=97_400_000.0, value_unit="USD")
    verdict, obs = decide(inr, usd)
    assert verdict.kind == RECONCILED
    assert obs.units_comparable is False


# --- guards against false positives ------------------------------------------

def test_a_level_and_a_growth_rate_are_never_the_same_claim():
    level = make_fact(id="a", value_num=8_142_000_000.0)
    growth = make_fact(
        id="b", doc_id="doc_b", metric_raw="revenue growth", derivative_kind="growth",
        value_raw="23.3%", value_num=23.3, value_unit="%", value_kind="percent",
    )
    assert decide(level, growth)[0].kind == RELATED


def test_non_overlapping_periods_are_a_time_series():
    fy24 = make_fact(id="a", value_num=8_142_000_000.0)
    fy23 = make_fact(
        id="b", doc_id="doc_b", value_raw="6,600", value_num=6_600_000_000.0,
        period_label="FY23", period_canonical="FY2023", period_start="2022-04-01",
        period_end="2023-03-31",
    )
    verdict, _ = decide(fy24, fy23)
    assert verdict.kind == RELATED
    assert verdict.dimension == "period"


def test_identical_categorical_values_corroborate():
    a = make_fact(id="a", fact_type="categorical", metric_raw="registered office",
                  value_raw="Bengaluru, Karnataka", value_num=None, value_unit="", value_kind="other")
    b = make_fact(id="b", doc_id="doc_b", fact_type="categorical", metric_raw="registered office",
                  value_raw="bengaluru, karnataka", value_num=None, value_unit="", value_kind="other")
    assert decide(a, b)[0].kind == CORROBORATES


def test_differing_categorical_values_are_escalated_not_auto_contradicted():
    """A director active in one document and resigned in a later one is a status
    change, which only the adjudicator can tell apart from a real conflict."""
    a = make_fact(id="a", fact_type="categorical", metric_raw="board role",
                  value_raw="Managing Director", value_num=None, value_unit="", value_kind="other")
    b = make_fact(id="b", doc_id="doc_b", fact_type="categorical", metric_raw="board role",
                  value_raw="resigned", value_num=None, value_unit="", value_kind="other")
    verdict, _ = decide(a, b)
    assert verdict.needs_llm is True


# --- regression: a whole document's linking once died here --------------------

def test_two_zero_values_do_not_crash_the_linker():
    """Both figures zero means the scale is zero, which left the relative
    difference undefined while every rationale formatted it as a percentage.
    That took down linking for an entire 941-fact document."""
    a = make_fact(id="a", value_raw="0", value_num=0.0)
    b = make_fact(id="b", doc_id="doc_b", value_raw="0", value_num=0.0,
                  qualifiers={"basis": "standalone"})
    verdict, obs = decide(a, b)
    assert obs.rel_diff == 0.0
    assert verdict.kind == CORROBORATES
    assert verdict.rationale and "0.00" in verdict.rationale


def test_rationales_never_crash_on_an_absent_difference():
    from factlayer.reconcile import Observation, classify as _classify
    a, b = make_fact(id="a"), make_fact(id="b", doc_id="doc_b")
    obs = Observation(metric_similarity=1.0, both_numeric=True, units_comparable=True,
                      value_a=1.0, value_b=2.0, rel_diff=None, period_relation="EQUAL")
    verdict = _classify(a, b, obs)
    assert isinstance(verdict.rationale, str) and verdict.rationale


def test_a_scale_suffix_attached_to_the_digits_is_not_lost():
    """'Rs 76Cr' has no word boundary between the digits and the suffix. Missing
    it dropped a factor of ten million and manufactured a false contradiction
    against a figure written 'Rs 92 Cr'."""
    from factlayer.normalize.units import parse_value
    assert parse_value("\u20b976Cr").number == 760_000_000.0
    assert parse_value("\u20b992 Cr").number == 920_000_000.0
    # ...without matching the "cr" buried inside an ordinary word.
    assert parse_value("an increase of 12%").number == 12.0
