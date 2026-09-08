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
