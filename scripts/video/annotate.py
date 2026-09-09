#!/usr/bin/env python
"""Turn raw screen recordings into an annotated screencast.

Two problems with a raw capture of a UI driven programmatically: it holds still
for long stretches between actions, and it explains nothing. This trims every
hold to a readable length and draws the explanation onto the frame itself —
a box around the thing being discussed and a short label beside it — so the
commentary sits on the interface rather than on a slide in front of it.

    python scripts/video/annotate.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
REC = ROOT / "build" / "rec"
WORK = ROOT / "build" / "work"
OUT = ROOT / "build" / "fact-knowledge-layer-demo.mp4"

W, H = 1920, 1080
CROP = "crop=1898:918:11:152"
# Where the cropped page lands inside the 16:9 frame after padding.
CONTENT_H = int(1920 * 918 / 1898)
PAD_Y = (H - CONTENT_H) // 2

# A hold carrying an annotation has to stay up long enough to read; one that
# carries nothing is dead air and should go. Trimming both to the same length
# either rushes the commentary or pads the gaps.
HOLD_ANNOTATED = 10.0
HOLD_PLAIN = 2.0
SPEED = 1.0

INK, MUTED = (245, 242, 235), (176, 170, 158)
ACCENT, WARN, GOOD = (110, 200, 188), (238, 156, 124), (140, 210, 156)
FONTS = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts")]


def font(name: str, size: int):
    for d in FONTS:
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), size)
    return ImageFont.load_default()


F_TITLE, F_BODY = font("Arial Bold.ttf", 33), font("Arial.ttf", 27)


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


def to_px(box):
    """Fractions of the visible page -> pixels in the padded frame."""
    x0, y0, x1, y1 = box
    return [x0 * W, PAD_Y + y0 * CONTENT_H, x1 * W, PAD_Y + y1 * CONTENT_H]


def overlay(note: dict) -> Image.Image:
    """One transparent annotation layer."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    colour = {"warn": WARN, "good": GOOD}.get(note.get("tone", ""), ACCENT)

    if note.get("box"):
        x0, y0, x1, y1 = to_px(note["box"])
        # Dim everything outside the focus so the eye goes to the right place.
        shade = Image.new("RGBA", (W, H), (8, 7, 5, 128))
        ImageDraw.Draw(shade).rounded_rectangle([x0, y0, x1, y1], 14, fill=(0, 0, 0, 0))
        layer.alpha_composite(shade)
        draw = ImageDraw.Draw(layer)
        draw.rounded_rectangle([x0, y0, x1, y1], 14, outline=colour + (255,), width=4)

    title, body = note.get("title", ""), note.get("body", "")
    pad, panel_w = 26, int(note.get("w", 0.40) * W)
    t_lines = wrap(draw, title, F_TITLE, panel_w - pad * 2) if title else []
    b_lines = wrap(draw, body, F_BODY, panel_w - pad * 2) if body else []
    height = pad * 2 + len(t_lines) * 42 + (8 if t_lines and b_lines else 0) + len(b_lines) * 36

    px, py = int(note.get("x", 0.05) * W), int(note.get("y", 0.05) * H)
    px = max(24, min(px, W - panel_w - 24))
    py = max(24, min(py, H - height - 24))

    box = Image.new("RGBA", (panel_w, height), (17, 16, 12, 243))
    layer.alpha_composite(box, (px, py))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle([px, py, px + panel_w, py + height], 12,
                           outline=(70, 68, 56, 255), width=2)
    draw.rectangle([px, py + 12, px + 6, py + height - 12], fill=colour + (255,))

    y = py + pad
    for line in t_lines:
        draw.text((px + pad + 14, y), line, font=F_TITLE, fill=INK + (255,)); y += 42
    if t_lines and b_lines:
        y += 8
    for line in b_lines:
        draw.text((px + pad + 14, y), line, font=F_BODY, fill=MUTED + (255,)); y += 36

    if note.get("box") and note.get("point"):
        x0, y0, x1, y1 = to_px(note["box"])
        ax = px + panel_w if px + panel_w < x0 else px
        ay = py + height // 2
        tx = x0 - 12 if ax < x0 else x1 + 12
        ty = (y0 + y1) / 2
        draw.line([(ax, ay), (tx, ty)], fill=colour + (255,), width=5)
    return layer


def build_keep_list(segments: list[dict], annotated: set[float]) -> list[tuple[float, float]]:
    """Keep every moving stretch, and as much of each hold as it has to say."""
    keep = []
    for seg in segments:
        if seg["kind"] == "motion":
            end = seg["end"]
        else:
            cap = HOLD_ANNOTATED if seg["start"] in annotated else HOLD_PLAIN
            end = min(seg["end"], seg["start"] + cap)
        if end - seg["start"] > 0.12:
            keep.append((seg["start"], round(end, 2)))
    merged = [list(keep[0])]
    for start, end in keep[1:]:
        if start - merged[-1][1] < 0.05:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(a, b) for a, b in merged]


# Which hold in each recording shows what, and what to say about it. Hold indices
# come from analyze.py; the boxes are fractions of the visible page.
PLAN = [
    {"src": "01_ingest.mp4", "notes": [
        {"hold": -1, "box": [0.17, 0.50, 0.83, 0.79], "point": True, "tone": "good",
         "x": 0.04, "y": 0.08, "w": 0.40,
         "title": "A PDF, processed end to end",
         "body": "Extract, verify every quote against the real page, resolve the entity, fold new metric names into the vocabulary, then link against everything already stored."},
    ]},
    {"src": "02_cases.mp4", "notes": [
        # Pinned to the longest holds: a caption needs time on screen, and the
        # short holds are transitions rather than moments worth explaining.
        {"hold": 4, "box": [0.18, 0.60, 0.82, 0.97], "point": True,
         "x": 0.05, "y": 0.08, "w": 0.44,
         "title": "Case 1 — corroborated across documents",
         "body": "The same figure in two filings two years apart: one writes crore, the other million. They agree to 0.01%, inside a tolerance derived from how precisely each was written."},
        {"hold": 5, "box": [0.30, 0.10, 0.70, 0.36], "point": True, "tone": "good",
         "x": 0.05, "y": 0.62, "w": 0.44,
         "title": "Grounded in the source",
         "body": "The model proposes a quote; the system finds it on the page before storing the fact. A quote it cannot find is rejected rather than trusted."},
        {"hold": 8, "box": [0.18, 0.06, 0.82, 0.45], "point": True, "tone": "warn",
         "x": 0.05, "y": 0.58, "w": 0.44,
         "title": "Case 2 — a genuine contradiction",
         "body": "Adjusted EBITDA for FY21, stated twice in one annual report and differing by 10.8 per cent, with no difference in basis, scope or period to account for it."},
        {"hold": 10, "box": [0.18, 0.55, 0.82, 0.98], "point": True, "tone": "good",
         "x": 0.05, "y": 0.08, "w": 0.44,
         "title": "Case 3 — explained by context",
         "body": "Both figures are right. One covers the first half of FY25, the other calendar 2024. Reconciled on period rather than reported as a conflict."},
        {"hold": 11, "box": [0.18, 0.30, 0.82, 0.72], "point": True,
         "x": 0.05, "y": 0.04, "w": 0.44,
         "title": "Case 4 — failures, measured",
         "body": "Rejected facts are kept with a reason. “Table association unverifiable” is a column-major table the extractor could not resolve — not a fabrication."},
        {"hold": 13, "box": [0.36, 0.28, 0.88, 0.95], "point": True,
         "x": 0.03, "y": 0.14, "w": 0.32,
         "title": "A schema grown from documents",
         "body": "107 qualifier keys, none declared up front. A document that introduces a new dimension registers it, and it takes part in comparison immediately."},
    ]},
    {"src": "03_detail.mp4", "notes": [
        {"hold": 1, "box": [0.18, 0.41, 0.81, 0.66], "point": True, "tone": "good",
         "x": 0.05, "y": 0.71, "w": 0.44,
         "title": "The arithmetic behind the verdict",
         "body": "Units reconciled onto one scale, both periods placed on a timeline, and a tolerance derived from how precisely each figure was written. Every decision shows its working."},
        {"hold": 2, "box": [0.18, 0.27, 0.82, 0.38], "point": True,
         "x": 0.05, "y": 0.50, "w": 0.44,
         "title": "2,685 links, all inspectable",
         "body": "Filter by kind, scope or metric. Roughly nine in ten verdicts come from deterministic rules; only the pairs those cannot settle are sent to a model."},
        {"hold": 3, "box": [0.18, 0.32, 0.82, 0.97], "point": True,
         "x": 0.05, "y": 0.06, "w": 0.42,
         "title": "3,112 facts, each tied to a source",
         "body": "Numbers, roles, addresses, ownership, dates. Every row carries the document and page it came from, and clicking one shows it highlighted on that page."},
    ]},
]


def render(src: str, notes: list[dict], index: int) -> Path:
    video = REC / src
    probe = json.loads(subprocess.run(
        [sys.executable, str(ROOT / "scripts/video/analyze.py"), str(video), CROP],
        capture_output=True, text=True, check=True).stdout)
    segments, holds = probe["segments"], probe["holds"]

    annotated = set()
    for note in notes:
        if note["hold"] == -1:
            tail = [s for s in segments if s["kind"] == "hold"]
            if tail:
                annotated.add(tail[-1]["start"])
        elif note["hold"] < len(holds):
            annotated.add(holds[note["hold"]]["start"])
    keep = build_keep_list(segments, annotated)

    # Where each kept range lands once the gaps are removed.
    timeline, cursor = [], 0.0
    for start, end in keep:
        timeline.append((start, end, cursor, cursor + (end - start)))
        cursor += end - start

    def remap(t: float) -> float | None:
        for s, e, ns, _ in timeline:
            if s <= t <= e:
                return ns + (t - s)
        return None

    filters, inputs, overlays = [], ["-i", str(video)], []
    select = "+".join(f"between(t,{s},{e})" for s, e, _, _ in timeline)
    filters.append(
        f"[0:v]{CROP},select='{select}',setpts=N/FRAME_RATE/TB,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x12110d,fps=30[base]"
    )

    stage = WORK / f"ov{index}"
    stage.mkdir(parents=True, exist_ok=True)
    last = "base"
    for n, note in enumerate(notes):
        if note["hold"] == -1:
            tail = [s for s in segments if s["kind"] == "hold"][-1]
            hold = {"start": tail["start"], "end": tail["end"]}
        else:
            if note["hold"] >= len(holds):
                continue
            hold = holds[note["hold"]]
        start = remap(hold["start"] + 0.15)
        end = remap(min(hold["end"], hold["start"] + HOLD_ANNOTATED) - 0.1)
        if start is None or end is None or end - start < 0.4:
            continue
        png = stage / f"{n:02d}.png"
        overlay(note).save(png)
        inputs += ["-i", str(png)]
        idx = len(inputs) // 2 - 1
        filters.append(
            f"[{last}][{idx}:v]overlay=0:0:enable='between(t,{start:.2f},{end:.2f})'[v{n}]"
        )
        last = f"v{n}"
        overlays.append((note.get("title", ""), round(start, 1), round(end, 1)))

    filters.append(f"[{last}]setpts=PTS/{SPEED},fps=30,format=yuv420p[out]")
    out = WORK / f"seg{index}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                    "-filter_complex", ";".join(filters), "-map", "[out]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out)], check=True)
    for title, a, b in overlays:
        print(f"    {a:6.1f}s - {b:5.1f}s  {title}")
    return out


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, block in enumerate(PLAN):
        print(f"  {block['src']}")
        parts.append(render(block["src"], block["notes"], i))
    listing = WORK / "parts.txt"
    listing.write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-c", "copy", str(OUT)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(OUT)], capture_output=True, text=True).stdout.strip()
    print(f"\nwrote {OUT}  {float(dur):.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
