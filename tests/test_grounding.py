"""Grounding is what separates "the model said so" from "the document says so"."""
from pathlib import Path

import pytest

from factlayer.pdf import PdfDocument

CORPUS = Path(__file__).resolve().parent.parent / "data_raw" / "starter-datasets"
SAMPLE = CORPUS / "delhivery" / "03-delhivery-q4-fy24-earnings-presentation.pdf"

pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="starter dataset not present")


@pytest.fixture(scope="module")
def pdf():
    with PdfDocument(SAMPLE) as doc:
        yield doc


def _a_real_line(pdf, page_no=5, min_len=45):
    for line in pdf.page_text(page_no).split("\n"):
        if len(line.strip()) >= min_len:
            return line.strip()
    pytest.skip("no suitable line on that page")


def test_a_real_quote_is_located_exactly(pdf):
    quote = _a_real_line(pdf)
    location = pdf.locate_evidence(quote, hint_page=5)
    assert location is not None
    assert location.page == 5
    assert location.match_ratio == 1.0
    assert location.verified is True
    assert location.rects, "a verified quote should yield highlight rectangles"


def test_an_invented_quote_is_rejected(pdf):
    """The single most important guard in the system: if the model fabricates a
    quote, the fact never enters the knowledge layer."""
    assert pdf.locate_evidence(
        "Delhivery reported unicorn revenues of forty two zillion rupees for the year",
        hint_page=5,
    ) is None


def test_a_quote_from_the_wrong_page_is_still_found_within_the_chunk(pdf):
    """Models cite the printed page number instead of the PDF index often enough
    that recovering the true page matters."""
    quote = _a_real_line(pdf, page_no=6)
    location = pdf.locate_evidence(quote, hint_page=999, candidate_pages=[4, 5, 6, 7])
    assert location is not None and location.page == 6


def test_chunking_respects_both_bounds(pdf):
    chunks = pdf.chunks(pages_per_chunk=4, char_budget=3000)
    assert chunks
    for chunk in chunks:
        assert len(chunk.pages) <= 4
        assert f"[[page {chunk.page_start}]]" in chunk.text
    covered = [p for chunk in chunks for p in chunk.pages]
    assert covered == sorted(set(covered)), "pages must be covered once, in order"
