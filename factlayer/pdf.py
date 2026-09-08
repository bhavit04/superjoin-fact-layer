"""PDF text extraction, chunking, and -- most importantly -- evidence grounding.

A fact is only worth something if you can point at the words that support it. The
extraction model returns a page number and a verbatim quote; both are claims by
the model, not facts about the document. ``locate_evidence`` checks them against
the actual page text and reports how well they matched. Facts whose quote cannot
be found anywhere near the cited page are flagged rather than trusted, which is
what turns "the model said so" into "the document says so".
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Iterator

import pymupdf as fitz

_WS = re.compile(r"\s+")
PAGE_MARKER = re.compile(r"\[\[page (\d+)\]\]")


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class Page:
    index: int          # 1-based index into the PDF file
    label: str          # the page number printed on the page, when the PDF declares one
    text: str
    char_count: int


@dataclass
class Chunk:
    ordinal: int
    page_start: int
    page_end: int
    text: str           # includes [[page N]] markers so the model can cite pages
    pages: list[int] = field(default_factory=list)


@dataclass
class EvidenceLocation:
    page: int
    rects: list[tuple[float, float, float, float]]
    match_ratio: float
    matched_text: str
    verified: bool


class PdfDocument:
    """A thin, lazily-read wrapper over a PDF that knows how to ground quotes."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._doc = fitz.open(self.path)
        self._page_text: dict[int, str] = {}

    def __enter__(self) -> "PdfDocument":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self._doc.close()
        except Exception:
            pass

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def metadata(self) -> dict:
        return dict(self._doc.metadata or {})

    def title_guess(self) -> str:
        """Prefer embedded metadata; fall back to the largest text on page 1."""
        meta_title = normalize_ws(self.metadata.get("title", ""))
        if meta_title and len(meta_title) > 4 and "untitled" not in meta_title.lower():
            return meta_title[:200]
        try:
            page = self._doc[0]
            spans: list[tuple[float, str]] = []
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = normalize_ws(span.get("text", ""))
                        if len(text) >= 4:
                            spans.append((span.get("size", 0.0), text))
            if spans:
                spans.sort(key=lambda s: -s[0])
                return " ".join(t for _, t in spans[:2])[:200]
        except Exception:
            pass
        return self.path.stem.replace("-", " ").replace("_", " ")[:200]

    def page_text(self, index: int) -> str:
        """1-based page text, cached."""
        if index not in self._page_text:
            self._page_text[index] = self._doc[index - 1].get_text("text")
        return self._page_text[index]

    def pages(self) -> Iterator[Page]:
        for i in range(self.page_count):
            page = self._doc[i]
            try:
                label = page.get_label() or str(i + 1)
            except Exception:
                label = str(i + 1)
            text = page.get_text("text")
            self._page_text[i + 1] = text
            yield Page(index=i + 1, label=label, text=text, char_count=len(text))

    # --- chunking ------------------------------------------------------------

    def chunks(self, pages_per_chunk: int = 4, char_budget: int = 14000) -> list[Chunk]:
        """Group pages into chunks bounded by both page count and character count.

        Two bounds rather than one because these corpora mix dense financial-note
        pages (10k+ chars) with sparse slide pages (300 chars). A pure page count
        would produce wildly uneven prompts; a pure character count would split
        mid-table more often than necessary.
        """
        out: list[Chunk] = []
        buf: list[Page] = []
        buf_chars = 0

        def flush() -> None:
            nonlocal buf, buf_chars
            if not buf:
                return
            body = "\n".join(f"[[page {p.index}]]\n{p.text}" for p in buf)
            out.append(
                Chunk(
                    ordinal=len(out),
                    page_start=buf[0].index,
                    page_end=buf[-1].index,
                    text=body,
                    pages=[p.index for p in buf],
                )
            )
            buf, buf_chars = [], 0

        for page in self.pages():
            if buf and (len(buf) >= pages_per_chunk or buf_chars + page.char_count > char_budget):
                flush()
            buf.append(page)
            buf_chars += page.char_count
        flush()
        return [c for c in out if normalize_ws(c.text.replace("[[page", "")) ]

    # --- grounding -----------------------------------------------------------

    def locate_evidence(
        self,
        quote: str,
        hint_page: int | None = None,
        search_window: int = 3,
        candidate_pages: list[int] | None = None,
    ) -> EvidenceLocation | None:
        """Find ``quote`` in the document and return where it is.

        Searches the hinted page first, then a small window around it, then gives
        up rather than scanning the whole document -- a quote that is nowhere near
        where the model said it was is itself a signal worth keeping.
        """
        quote = normalize_ws(quote)
        if len(quote) < 12:
            return None

        candidates: list[int] = []
        if hint_page and 1 <= hint_page <= self.page_count:
            candidates.append(hint_page)
            for offset in range(1, search_window + 1):
                for page in (hint_page - offset, hint_page + offset):
                    if 1 <= page <= self.page_count:
                        candidates.append(page)
        # The model cites the [[page N]] marker, but these excerpt PDFs also print
        # their *original* page numbers, which the model sometimes copies instead.
        # Falling back to the chunk's own page range recovers those cases.
        for page in candidate_pages or []:
            if 1 <= page <= self.page_count and page not in candidates:
                candidates.append(page)
        if not candidates:
            candidates = list(range(1, self.page_count + 1))

        best: EvidenceLocation | None = None
        for page_no in candidates:
            location = self._locate_on_page(quote, page_no)
            if location is None:
                continue
            if best is None or location.match_ratio > best.match_ratio:
                best = location
            if best.match_ratio >= 0.99:
                break
        return best

    def _locate_on_page(self, quote: str, page_no: int) -> EvidenceLocation | None:
        page = self._doc[page_no - 1]
        page_text = normalize_ws(self.page_text(page_no))
        if not page_text:
            return None

        # Exact (whitespace-insensitive) containment is the common, happy path.
        if quote.lower() in page_text.lower():
            rects = self._rects_for(page, quote)
            return EvidenceLocation(page_no, rects, 1.0, quote, verified=True)

        # Otherwise slide a window the length of the quote across the page and take
        # the best fuzzy match. PDF extraction reorders and hyphenates text often
        # enough that exact matching alone would reject a lot of true evidence.
        ratio, matched = _best_window_match(quote, page_text)
        if ratio < 0.62:
            return None
        rects = self._rects_for(page, matched)
        return EvidenceLocation(page_no, rects, round(ratio, 3), matched, verified=ratio >= 0.80)

    @staticmethod
    def _rects_for(page: "fitz.Page", quote: str) -> list[tuple[float, float, float, float]]:
        """Best-effort highlight rectangles. Long quotes rarely match as one run,
        so we fall back to locating the first and last fragments."""
        try:
            hits = page.search_for(quote[:180], quads=False)
            if hits:
                return [tuple(round(v, 2) for v in r) for r in hits[:8]]
        except Exception:
            pass
        rects: list[tuple[float, float, float, float]] = []
        for fragment in _fragments(quote, 42):
            try:
                hits = page.search_for(fragment, quads=False)
            except Exception:
                hits = []
            if hits:
                rects.append(tuple(round(v, 2) for v in hits[0]))
            if len(rects) >= 8:
                break
        return rects

    def render_page_png(
        self, page_no: int, rects: Iterable[tuple[float, float, float, float]] = (), zoom: float = 2.0
    ) -> bytes:
        """Render a page to PNG with the evidence rectangles highlighted."""
        page = self._doc[page_no - 1]
        for rect in rects or []:
            try:
                annot = page.add_highlight_annot(fitz.Rect(*rect))
                annot.set_colors(stroke=(1.0, 0.85, 0.2))
                annot.update(opacity=0.45)
            except Exception:
                continue
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")


def _fragments(text: str, size: int) -> list[str]:
    words, out, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > size:
            if current:
                out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out


def _best_window_match(needle: str, haystack: str) -> tuple[float, str]:
    """Best fuzzy alignment of ``needle`` inside ``haystack``.

    Uses SequenceMatcher's longest-block anchor to pick where to compare, which is
    far cheaper than scoring every offset and good enough for locating a sentence.
    """
    if not needle or not haystack:
        return 0.0, ""
    matcher = SequenceMatcher(None, needle.lower(), haystack.lower(), autojunk=False)
    block = matcher.find_longest_match(0, len(needle), 0, len(haystack))
    if block.size < 12:
        return 0.0, ""
    start = max(0, block.b - block.a)
    window = haystack[start : start + len(needle) + 20]
    ratio = SequenceMatcher(None, needle.lower(), window.lower(), autojunk=False).ratio()
    return ratio, window
