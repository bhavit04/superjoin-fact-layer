#!/usr/bin/env python
"""Turn raw screen recordings into an annotated screencast.

Three things this does that a plain capture cannot.

*Pacing.* Driving a UI programmatically leaves long motionless gaps. Each beat
keeps the action that caused a state plus as much of the resulting hold as its
caption needs to be read, and drops the rest.

*Alignment.* Highlight boxes are measured off the frame rather than guessed:
the app's cards sit at a distinctly lighter tone than the page, so a seed point
inside a card snaps outward to that card's true edges. Hand-placed fractions
drifted as the layout scrolled, which is what made boxes overflow their content.

*Narrative.* Beats are rendered individually and ordered by argument -- what the
system does, what it produced, why you can trust it, then the four cases -- not
by the order they happened to be recorded in.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
REC, WORK = ROOT / "build" / "rec", ROOT / "build" / "work"
OUT = ROOT / "build" / "fact-knowledge-layer-demo.mp4"

W, H = 1920, 1080
CROP_W, CROP_H, CROP_X, CROP_Y = 1898, 918, 11, 152
CROP = f"crop={CROP_W}:{CROP_H}:{CROP_X}:{CROP_Y}"
SCALE = W / CROP_W                      # the crop is width-limited in a 16:9 frame
CONTENT_H = int(CROP_H * SCALE)
PAD_Y = (H - CONTENT_H) // 2

LEAD_IN = 1.3                            # seconds of the action that produced a state
HOLD = 13.0                               # seconds a state with a caption stays up

INK, MUTED = (245, 242, 235), (178, 172, 160)
ACCENT, WARN, GOOD = (110, 200, 188), (238, 156, 124), (140, 210, 156)
FONT_DIRS = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts")]


def font(name: str, size: int):
    for d in FONT_DIRS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default()


F_TITLE, F_BODY = font("Arial Bold.ttf", 34), font("Arial.ttf", 28)


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        t = f"{cur} {word}".strip()
        if draw.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur); cur = word
    if cur:
        lines.append(cur)
    return lines


# --- finding the thing being pointed at --------------------------------------

def card_bounds(frame: np.ndarray, seed: tuple[float, float]) -> tuple[int, int, int, int]:
    """Snap a rough seed point outward to the edges of the card containing it.

    Cards render a few tones lighter than the page, so thresholding and then
    walking out from the seed along rows and columns finds the real boundary.
    Coverage is measured per row and per column rather than pixel by pixel,
    because text and inner panels break up any single scan line.
    """
    h, w = frame.shape[:2]
    mask = frame.mean(axis=2) > 19.0
    sx, sy = int(seed[0] * w), int(seed[1] * h)
    sx, sy = max(1, min(sx, w - 2)), max(1, min(sy, h - 2))

    rows = mask[:, int(w * 0.22): int(w * 0.78)].mean(axis=1)
    cols = mask[max(0, sy - 40): sy + 40, :].mean(axis=0)

    def run(profile, start, floor):
        lo = hi = start
        while lo > 0 and profile[lo - 1] >= floor:
            lo -= 1
        while hi < len(profile) - 1 and profile[hi + 1] >= floor:
            hi += 1
        return lo, hi

    # A seed can land on a sparse row -- a gap between fields, or a line of small
    # text -- and collapse the walk to nothing. Relax the threshold until the
    # region found is big enough to be a card rather than a line.
    y0 = y1 = sy
    for floor in (0.45, 0.30, 0.18, 0.10):
        y0, y1 = run(rows, sy, floor)
        if y1 - y0 >= 60:
            break
    else:
        y0, y1 = max(0, sy - 120), min(h - 1, sy + 120)

    x0 = x1 = sx
    for floor in (0.35, 0.22, 0.12):
        x0, x1 = run(cols, sx, floor)
        if x1 - x0 >= 200:
            break
    # Cards are page-width; a narrow result means the walk stopped inside one.
    if x1 - x0 < w * 0.3:
        x0, x1 = int(w * 0.185), int(w * 0.812)
    return x0, y0, x1, y1


def to_frame(box: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (x0 * SCALE, PAD_Y + y0 * SCALE, x1 * SCALE, PAD_Y + y1 * SCALE)


# --- drawing -----------------------------------------------------------------

def overlay(note: dict, box_px: tuple[float, float, float, float]) -> Image.Image:
    """A dimmed frame with the focus cut out, and a caption anchored beside it.

    The caption is a tooltip with a caret on the edge facing its subject, rather
    than a floating panel joined by a long diagonal line. A short caret reads as
    "this label belongs to that box"; a diagonal arrow across the screen reads as
    a distraction.
    """
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = box_px
    colour = {"warn": WARN, "good": GOOD}.get(note.get("tone", ""), ACCENT)

    shade = Image.new("RGBA", (W, H), (8, 7, 5, 130))
    ImageDraw.Draw(shade).rounded_rectangle([x0, y0, x1, y1], 12, fill=(0, 0, 0, 0))
    layer.alpha_composite(shade)
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle([x0, y0, x1, y1], 12, outline=colour + (255,), width=4)

    pad, panel_w = 26, int(note.get("w", 0.42) * W)
    t_lines = wrap(draw, note.get("title", ""), F_TITLE, panel_w - pad * 2 - 16)
    b_lines = wrap(draw, note.get("body", ""), F_BODY, panel_w - pad * 2 - 16)
    height = pad * 2 + len(t_lines) * 44 + (10 if t_lines and b_lines else 0) + len(b_lines) * 37

    # Sit the caption in whichever margin the box leaves free. A box that spans
    # the page can only be captioned above or below it; a narrower one -- a modal,
    # a column -- has room beside it, which keeps the caption off the content the
    # box is drawing attention to.
    gap, caret = 26, 16
    spans_page = (x1 - x0) > W * 0.6
    py = side = px = None

    if not spans_page:
        cy = int((y0 + y1) / 2 - height / 2)
        cy = max(24, min(cy, H - height - 24))
        if x0 - gap - panel_w >= 40:
            px, py, side = int(x0) - gap - panel_w, cy, "right"   # caret on the right edge
        elif x1 + gap + panel_w <= W - 40:
            px, py, side = int(x1) + gap, cy, "left"

    if py is None:
        above, below = int(y0) - gap - height, int(y1) + gap
        if above >= 24:
            py, side = above, "below"
        elif below + height <= H - 24:
            py, side = below, "above"
        else:
            py, side = max(24, min(int(H * 0.06), H - height - 24)), None
        px = int(min(max((x0 + x1) / 2 - panel_w / 2, 40), W - panel_w - 40))

    panel = Image.new("RGBA", (panel_w, height), (17, 16, 12, 246))
    layer.alpha_composite(panel, (px, py))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle([px, py, px + panel_w, py + height], 12,
                           outline=(74, 72, 60, 255), width=2)
    draw.rectangle([px, py + 14, px + 6, py + height - 14], fill=colour + (255,))

    if side in {"below", "above"}:
        cx = min(max((x0 + x1) / 2, px + 60), px + panel_w - 60)
        if side == "below":
            draw.polygon([(cx - caret, py + height), (cx + caret, py + height),
                          (cx, py + height + caret)], fill=(17, 16, 12, 246))
        else:
            draw.polygon([(cx - caret, py), (cx + caret, py), (cx, py - caret)],
                         fill=(17, 16, 12, 246))
    elif side in {"left", "right"}:
        cy2 = min(max((y0 + y1) / 2, py + 50), py + height - 50)
        if side == "right":
            draw.polygon([(px + panel_w, cy2 - caret), (px + panel_w, cy2 + caret),
                          (px + panel_w + caret, cy2)], fill=(17, 16, 12, 246))
        else:
            draw.polygon([(px, cy2 - caret), (px, cy2 + caret), (px - caret, cy2)],
                         fill=(17, 16, 12, 246))

    y = py + pad
    for line in t_lines:
        draw.text((px + pad + 14, y), line, font=F_TITLE, fill=INK + (255,)); y += 44
    if t_lines and b_lines:
        y += 10
    for line in b_lines:
        draw.text((px + pad + 14, y), line, font=F_BODY, fill=MUTED + (255,)); y += 37
    return layer


# --- the demo, in the order it should be understood ---------------------------

BEATS = [
    {"src": "01_ingest", "hold": "last", "seed": [0.5, 0.60], "tone": "good",
     "title": "A PDF, processed end to end",
     "body": "Extract, verify every quote against the real page, resolve the entity, fold new metric names into the vocabulary, then link against everything already stored."},

    {"src": "03_detail", "hold": 3, "seed": [0.5, 0.62],
     "title": "3,112 facts, each tied to a source",
     "body": "Numbers, roles, addresses, ownership, dates. Every row carries the document and page it came from."},

    {"src": "02_cases", "hold": 5, "seed": [0.5, 0.30], "tone": "good",
     "title": "Grounded in the source",
     "body": "The model proposes a quote; the system finds it on the page before storing the fact. A quote it cannot find is rejected rather than trusted."},

    {"src": "02_cases", "hold": 4, "seed": [0.5, 0.78],
     "title": "Case 1 — corroborated across documents",
     "body": "The same figure in two filings two years apart: one writes crore, the other million."},

    {"src": "03_detail", "hold": 1, "seed": [0.5, 0.52], "tone": "good",
     "title": "Why they agree",
     "body": "Units reconciled onto one scale, both periods placed on a timeline, and a tolerance derived from how precisely each figure was written."},

    {"src": "02_cases", "hold": 8, "seed": [0.5, 0.22], "tone": "warn",
     "title": "Case 2 — a genuine contradiction",
     "body": "Adjusted EBITDA for FY21, stated twice in one annual report and differing by 10.8 per cent, with nothing in either source to account for it."},

    {"src": "02_cases", "hold": 10, "seed": [0.5, 0.78], "tone": "good",
     "title": "Case 3 — explained by context",
     "body": "Both figures are right. One covers the first half of FY25, the other calendar 2024. Reconciled on period rather than reported as a conflict."},

    {"src": "02_cases", "hold": 11, "seed": [0.5, 0.45],
     "title": "Case 4 — failures, measured",
     "body": "Rejected facts are kept with a reason. “Table association unverifiable” is a column-major table the extractor could not resolve, not a fabrication."},

    {"src": "02_cases", "hold": 13, "seed": [0.62, 0.55],
     "title": "A schema grown from documents",
     "body": "107 qualifier keys, none declared up front. A document that introduces a new dimension registers it, and it takes part in comparison immediately."},

    {"src": "03_detail", "hold": 2, "seed": [0.5, 0.55],
     "title": "2,685 links, all inspectable",
     "body": "Roughly nine in ten verdicts come from deterministic rules; only the pairs those cannot settle are sent to a model."},
]


# --- rendering ---------------------------------------------------------------

def probe(src: str) -> dict:
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts/video/analyze.py"), str(REC / f"{src}.mp4"), CROP],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def grab(src: str, t: float) -> np.ndarray:
    """One cropped frame as an array, for measuring."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(REC / f"{src}.mp4"),
         "-vf", CROP, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(CROP_H, CROP_W, 3).astype(int)


def render_beat(beat: dict, index: int, cache: dict) -> Path:
    src = beat["src"]
    data = cache.setdefault(src, probe(src))
    holds, segments = data["holds"], data["segments"]

    if beat["hold"] == "last":
        hold = [s for s in segments if s["kind"] == "hold"][-1]
    else:
        hold = holds[beat["hold"]]

    # Include the movement that produced this state, so a cut has a cause.
    lead = 0.0
    for seg in segments:
        if seg["kind"] == "motion" and abs(seg["end"] - hold["start"]) < 0.35:
            lead = min(LEAD_IN, seg["dur"])
            break
    start = max(0.0, hold["start"] - lead)
    duration = lead + min(HOLD, hold["dur"])

    frame = grab(src, hold["start"] + 0.6)
    box = to_frame(card_bounds(frame, beat["seed"]))

    png = WORK / f"beat{index:02d}.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    overlay(beat, box).save(png)

    out = WORK / f"beat{index:02d}.mp4"
    fade_in = round(lead, 2)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.2f}", "-t", f"{duration:.2f}", "-i", str(REC / f"{src}.mp4"),
        # The still has to be looped, or the annotation shows for one frame.
        "-loop", "1", "-t", f"{duration:.2f}", "-i", str(png),
        "-filter_complex",
        f"[0:v]{CROP},scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x12110d,fps=30[base];"
        # Hold the annotation back until the movement has settled.
        f"[1:v]format=rgba,fade=in:st={fade_in:.2f}:d=0.35:alpha=1[note];"
        f"[base][note]overlay=0:0:format=auto,format=yuv420p[out]",
        "-map", "[out]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out),
    ], check=True)
    print(f"  {index:2}. {beat['title'][:46]:48} {duration:5.1f}s   box "
          f"{box[0]:.0f},{box[1]:.0f} -> {box[2]:.0f},{box[3]:.0f}")
    return out


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    for old in WORK.glob("beat*"):
        old.unlink()
    cache: dict = {}
    parts = [render_beat(b, i, cache) for i, b in enumerate(BEATS)]

    listing = WORK / "beats.txt"
    listing.write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(OUT)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(OUT)], capture_output=True, text=True).stdout.strip()
    print(f"\nwrote {OUT}  {float(dur):.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
