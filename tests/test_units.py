import pytest

from factlayer.normalize.units import humanize, parse_value, to_common_unit


@pytest.mark.parametrize("raw,expected", [
    ("Rs. 8,142 Mn", 8_142_000_000.0),
    ("₹ 814.2 crore", 8_142_000_000.0),
    ("INR 81,420 lakh", 8_142_000_000.0),
    ("$97.4 million", 97_400_000.0),
    ("1,23,456", 123_456.0),          # Indian digit grouping
    ("(1,234)", -1234.0),             # accounting negative
    ("12.5%", 12.5),
])
def test_magnitudes(raw, expected):
    assert parse_value(raw).number == pytest.approx(expected)


def test_scale_words_make_different_wordings_equal():
    """The corroboration case: same quantity, three ways of writing it."""
    a, b, c = parse_value("Rs. 8,142 Mn"), parse_value("₹ 814.2 crore"), parse_value("INR 81,420 lakh")
    assert a.number == b.number == c.number
    assert a.unit == b.unit == c.unit == "INR"


def test_currency_detection_is_longest_match():
    assert parse_value("US$ 3.2 billion").unit == "USD"
    assert parse_value("Rs. 500").unit == "INR"
    # "rs" must not fire inside an unrelated word.
    assert parse_value("5 years").unit == "years"


def test_ranges():
    value = parse_value("6.3 to 6.8 per cent")
    assert value.is_range and value.low == 6.3 and value.high == 6.8
    assert value.number == pytest.approx(6.55)


def test_fiscal_year_is_not_a_range():
    """'2023-24' is a period label, not a numeric range."""
    assert parse_value("2023-24").is_range is False


def test_unit_hint_from_table_header():
    value = parse_value("12,480", unit_hint="figures in INR million")
    assert value.unit == "INR"
    assert value.number == pytest.approx(12_480_000_000.0)


def test_bps_and_percent_are_reconcilable():
    a, b = parse_value("450 bps"), parse_value("4.5%")
    common = to_common_unit(a, b)
    assert common is not None
    assert common[0] == pytest.approx(common[1])


def test_different_currencies_are_not_comparable():
    """Returning None here is the point: INR vs USD is a currency difference,
    which the reconciler must explain rather than call a contradiction."""
    assert to_common_unit(parse_value("Rs 100 crore"), parse_value("$12 million")) is None


def test_humanize_uses_indian_scale_for_rupees():
    assert "crore" in humanize(8_142_000_000.0, "INR")


@pytest.mark.parametrize("raw,expected", [
    ("Rs. (452 Cr)", -4_520_000_000.0),   # parentheses wrap the number, not the string
    ("₹(452) Cr", -4_520_000_000.0),
    ("(4,516)", -4516.0),
    ("(6.3%)", -6.3),
])
def test_accounting_negatives_inside_a_longer_string(raw, expected):
    """A loss written 'Rs. (452 Cr)' was read as a profit, which then contradicted
    the same loss written '(4,516)' elsewhere in the corpus."""
    assert parse_value(raw).number == pytest.approx(expected)


@pytest.mark.parametrize("raw,expected", [
    ("12.7%(2)", 12.7),
    ("₹8,142 Cr(2)", 81_420_000_000.0),
])
def test_footnote_markers_are_not_read_as_negatives(raw, expected):
    assert parse_value(raw).number == pytest.approx(expected)
