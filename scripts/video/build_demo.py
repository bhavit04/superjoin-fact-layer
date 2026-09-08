#!/usr/bin/env python
"""Compose an annotated demo video from captured UI frames.

A silent demo has to explain itself on screen, so this does what a presenter's
cursor and voice would otherwise do: dim everything except the region under
discussion, point an arrow at it, and put the explanation beside it rather than
in a caption bar at the bottom.

Geometry is given in fractions of the source screenshot, so a storyboard written
against one capture still lines up if the capture is retaken at another size.

    python scripts/video/build_demo.py [storyboard.json]
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent.parent
FRAMES = ROOT / "build" / "frames"
STAGE = ROOT / "build" / "stage"
OUT = ROOT / "build" / "fact-knowledge-layer-demo.mp4"

W, H = 1920, 1080
BG        = (18, 17, 13)
INK       = (243, 240, 232)
MUTED     = (154, 148, 136)
ACCENT    = (110, 200, 188)
ACCENT_DK = (26, 58, 54)
WARN      = (232, 150, 120)
GOOD      = (135, 205, 150)

FONT_DIRS = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts")]


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        candidate = directory / name
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


F_HERO   = _font("Arial Bold.ttf", 88)
F_TITLE  = _font("Arial Bold.ttf", 64)
F_SUB    = _font("Arial.ttf", 36)
F_CALL   = _font("Arial Bold.ttf", 30)
F_BODY   = _font("Arial.ttf", 27)
F_TAG    = _font("Arial Bold.ttf", 22)
F_STEP   = _font("Arial Bold.ttf", 20)


def wrap(draw, text, font, max_width):
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# --- title cards -------------------------------------------------------------

def title_card(item: dict) -> Image.Image:
    card = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(card)

    # A faint accent wash so cards do not read as dead black.
    glow = Image.new("RGB", (W, H), BG)
    ImageDraw.Draw(glow).ellipse([-460, 300, 900, 1500], fill=(26, 44, 42))
    card = Image.blend(card, glow.filter(ImageFilter.GaussianBlur(180)), 0.55)
    draw = ImageDraw.Draw(card)

    x = 200
    y = 300 if item.get("subtitle") else 380

    if item.get("tag"):
        tag = item["tag"].upper()
        tw = draw.textlength(tag, font=F_TAG)
        draw.rounded_rectangle([x, y, x + tw + 40, y + 48], 24, fill=ACCENT_DK)
        draw.text((x + 20, y + 12), tag, font=F_TAG, fill=ACCENT)
        y += 92

    font = F_HERO if item.get("hero") else F_TITLE
    for line in wrap(draw, item["title"], font, W - 2 * x):
        draw.text((x, y), line, font=font, fill=INK)
        y += font.size + 18

    if item.get("subtitle"):
        y += 26
        draw.line([(x, y), (x + 132, y)], fill=ACCENT, width=5)
        y += 46
        for line in wrap(draw, item["subtitle"], F_SUB, W - 2 * x - 180):
            draw.text((x, y), line, font=F_SUB, fill=MUTED)
            y += 52
    return card


# --- annotated screenshots ---------------------------------------------------

def _place(shot: Image.Image, crop: list | None) -> tuple[Image.Image, tuple[int, int], float]:
    """Crop, scale and centre a screenshot; return it with its placement."""
    if crop:
        left, top, right, bottom = (
            int(crop[0] * shot.width), int(crop[1] * shot.height),
            int(crop[2] * shot.width), int(crop[3] * shot.height),
        )
        shot = shot.crop((left, top, max(left + 8, right), max(top + 8, bottom)))
    margin_y = 120
    scale = min((W - 160) / shot.width, (H - margin_y * 2) / shot.height)
    scale = min(scale, 2.4)
    size = (max(1, int(shot.width * scale)), max(1, int(shot.height * scale)))
    resized = shot.resize(size, Image.LANCZOS)
    origin = ((W - size[0]) // 2, (H - size[1]) // 2)
    return resized, origin, scale


def _to_canvas(point, origin, size):
    """Fractional coordinates within the placed screenshot -> canvas pixels."""
    return (origin[0] + point[0] * size[0], origin[1] + point[1] * size[1])


def _arrow(draw, start, end, colour=ACCENT, width=5, head=26):
    draw.line([start, end], fill=colour, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for spread in (0.42, -0.42):
        draw.line([end, (end[0] - head * math.cos(angle + spread),
                         end[1] - head * math.sin(angle + spread))], fill=colour, width=width)


def _callout(canvas, draw, box, text, title="", colour=ACCENT):
    """A text panel with a coloured edge, sized to its content."""
    x, y, max_w = box
    lines_title = wrap(draw, title, F_CALL, max_w - 56) if title else []
    lines_body = wrap(draw, text, F_BODY, max_w - 56) if text else []
    height = 34 + len(lines_title) * 40 + (10 if lines_title and lines_body else 0) + len(lines_body) * 36 + 30

    panel = Image.new("RGBA", (max_w, height), (24, 23, 18, 242))
    canvas.paste(Image.alpha_composite(
        canvas.crop((x, y, x + max_w, y + height)).convert("RGBA"), panel).convert("RGB"), (x, y))
    draw.rounded_rectangle([x, y, x + max_w, y + height], 14, outline=(60, 58, 48), width=2)
    draw.rectangle([x, y + 12, x + 6, y + height - 12], fill=colour)

    ty = y + 26
    for line in lines_title:
        draw.text((x + 32, ty), line, font=F_CALL, fill=INK)
        ty += 40
    if lines_title and lines_body:
        ty += 10
    for line in lines_body:
        draw.text((x + 32, ty), line, font=F_BODY, fill=MUTED)
        ty += 36
    return height


def screen_frame(item: dict) -> Image.Image:
    source = FRAMES / item["image"]
    shot = Image.open(source).convert("RGB")
    placed, origin, _ = _place(shot, item.get("crop"))
    size = placed.size

    canvas = Image.new("RGB", (W, H), BG)
    canvas.paste(placed, origin)

    # Spotlight: dim everything but the region being discussed.
    spots = item.get("spotlight") or []
    if spots:
        veil = Image.new("RGBA", (W, H), (10, 9, 7, 165))
        mask = ImageDraw.Draw(veil)
        for spot in spots:
            a = _to_canvas((spot[0], spot[1]), origin, size)
            b = _to_canvas((spot[2], spot[3]), origin, size)
            mask.rounded_rectangle([a[0] - 10, a[1] - 10, b[0] + 10, b[1] + 10], 16, fill=(0, 0, 0, 0))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), veil).convert("RGB")

    draw = ImageDraw.Draw(canvas)

    for spot in spots:
        a = _to_canvas((spot[0], spot[1]), origin, size)
        b = _to_canvas((spot[2], spot[3]), origin, size)
        draw.rounded_rectangle([a[0] - 10, a[1] - 10, b[0] + 10, b[1] + 10], 16,
                               outline=ACCENT, width=4)

    for note in item.get("callouts", []):
        colour = {"warn": WARN, "good": GOOD}.get(note.get("tone", ""), ACCENT)
        px = int(note.get("x", 0.04) * W)
        py = int(note.get("y", 0.06) * H)
        width = int(note.get("w", 0.32) * W)
        height = _callout(canvas, draw, (px, py, width), note.get("body", ""),
                          note.get("title", ""), colour)
        if note.get("arrow_to"):
            target = _to_canvas(tuple(note["arrow_to"]), origin, size)
            anchor = (px + width, py + height // 2) if target[0] > px + width else (px, py + height // 2)
            _arrow(draw, anchor, target, colour)

    if item.get("step"):
        draw.rounded_rectangle([64, 52, 64 + 46 + draw.textlength(item["step"], font=F_STEP), 100],
                               20, fill=ACCENT_DK)
        draw.text((88, 66), item["step"], font=F_STEP, fill=ACCENT)
    return canvas


# --- assembly ----------------------------------------------------------------

def build(spec: list[dict]) -> None:
    STAGE.mkdir(parents=True, exist_ok=True)
    for old in STAGE.glob("*.png"):
        old.unlink()

    entries, total = [], 0.0
    for index, item in enumerate(spec):
        try:
            image = title_card(item) if item["kind"] == "title" else screen_frame(item)
        except FileNotFoundError:
            print(f"  ! missing capture for step {index}: {item.get('image')}", file=sys.stderr)
            continue
        path = STAGE / f"{index:03d}.png"
        image.save(path)
        seconds = float(item.get("seconds", 5))
        entries.append((path, seconds))
        total += seconds

    playlist = STAGE / "playlist.txt"
    lines = []
    for path, seconds in entries:
        lines.append(f"file '{path}'")
        lines.append(f"duration {seconds}")
    if entries:
        lines.append(f"file '{entries[-1][0]}'")
    playlist.write_text("\n".join(lines), encoding="utf-8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(playlist),
        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-movflags", "+faststart", str(OUT),
    ], check=True)
    print(f"wrote {OUT}  —  {int(total // 60)}m{int(total % 60):02d}s, "
          f"{OUT.stat().st_size / 1e6:.1f} MB, {len(entries)} shots")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "storyboard.json"
    build(json.loads(path.read_text(encoding="utf-8")))
