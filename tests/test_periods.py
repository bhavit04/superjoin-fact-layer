import pytest

from factlayer.normalize.periods import (
    CONTAINED_BY, DISJOINT, EQUAL, compare_periods, parse_period,
)


@pytest.mark.parametrize("raw", [
    "FY24", "FY2024", "FY 2023-24", "2023-24", "for the year ended March 31, 2024",
])
def test_all_the_ways_a_document_names_one_fiscal_year(raw):
    """These five spellings appear across the starter corpus and must unify."""
    period = parse_period(raw)
    assert (period.start, period.end) == ("2023-04-01", "2024-03-31")
    assert period.canonical == "FY2024"


def test_equivalent_spellings_compare_equal():
    assert compare_periods(parse_period("FY24"), parse_period("the year ended March 31, 2024")) == EQUAL


def test_quarter_nests_inside_its_fiscal_year():
    assert compare_periods(parse_period("Q4 FY24"), parse_period("FY24")) == CONTAINED_BY


@pytest.mark.parametrize("raw,start,end", [
    ("Q1 FY25", "2024-04-01", "2024-06-30"),
    ("Q4 FY24", "2024-01-01", "2024-03-31"),
    ("H1 FY24", "2023-04-01", "2023-09-30"),
])
def test_indian_fiscal_quarters(raw, start, end):
    period = parse_period(raw)
    assert (period.start, period.end) == (start, end)


def test_consecutive_years_do_not_overlap():
    assert compare_periods(parse_period("FY24"), parse_period("FY23")) == DISJOINT


def test_balance_sheet_dates_are_points_not_periods():
    period = parse_period("as at March 31, 2024")
    assert period.is_point and period.start == period.end == "2024-03-31"


def test_bare_year_is_flagged_ambiguous():
    """A lone '2024' could be calendar or fiscal; the flag lets the adjudicator know."""
    assert parse_period("2024").fiscal_ambiguous is True
    assert parse_period("FY2024").fiscal_ambiguous is False


# --- generalizing beyond the starter corpus ----------------------------------

def test_fiscal_year_convention_is_read_from_the_document():
    """April-March is the Indian convention, not a universal one. A filing with a
    December year end means January-December by 'FY2024', and assuming otherwise
    shifts every period comparison against it by a quarter."""
    from factlayer.normalize.periods import detect_fiscal_year_start, parse_period

    indian = "for the year ended March 31, 2024 the Company reported"
    american = "for the fiscal year ended December 31, 2024 the Company reported"
    assert detect_fiscal_year_start(indian) == 4
    assert detect_fiscal_year_start(american) == 1

    india = parse_period("FY2024", fy_start=4)
    assert (india.start, india.end) == ("2023-04-01", "2024-03-31")
    usa = parse_period("FY2024", fy_start=1)
    assert (usa.start, usa.end) == ("2024-01-01", "2024-12-31")
    # Quarters follow the same convention.
    assert parse_period("Q4 FY2024", fy_start=1).start == "2024-10-01"
    assert parse_period("Q4 FY2024", fy_start=4).start == "2024-01-01"


def test_an_unrecognizable_document_keeps_the_default_convention():
    from factlayer.normalize.periods import detect_fiscal_year_start
    assert detect_fiscal_year_start("no year-end phrasing here at all") == 4


def test_a_month_range_is_not_its_final_month():
    """'April to December 2024' is nine months. Collapsing it to December made a
    nine-month capital-flow figure look like it contradicted a one-month one."""
    from factlayer.normalize.periods import CONTAINS, compare_periods, parse_period
    span = parse_period("April to December 2024")
    assert (span.start, span.end) == ("2024-04-01", "2024-12-31")
    assert compare_periods(span, parse_period("December 2024")) == CONTAINS
    # A range that wraps a year boundary starts in the earlier year.
    assert parse_period("November to February 2025").start == "2024-11-01"
