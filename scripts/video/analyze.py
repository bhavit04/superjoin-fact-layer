#!/usr/bin/env python
"""Find where a screen recording is holding still.

Driving a UI programmatically produces long motionless stretches between actions,
which is what makes a raw capture feel slow. Sampling the frames and measuring
how much changes between them separates the recording into motion and holds, so
the holds can be trimmed to a readable length and annotations can be pinned to
the moment a state is actually on screen.

    python scripts/video/analyze.py <video> [crop]
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

FPS = 10          # sampling rate for the analysis, not the output
W, H = 160, 90
MOTION = 2.2      # mean abs difference above this counts as movement


def sample(path: str, crop: str | None) -> np.ndarray:
    chain = f"{crop}," if crop else ""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-vf", f"{chain}fps={FPS},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True, check=True,
    )
    data = np.frombuffer(proc.stdout, dtype=np.uint8)
    return data[: len(data) // (W * H) * W * H].reshape(-1, H, W).astype(np.int16)


def segments(frames: np.ndarray) -> list[dict]:
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    moving = diffs > MOTION
    out, start, state = [], 0, bool(moving[0])
    for i in range(1, len(moving)):
        if bool(moving[i]) != state:
            out.append({"kind": "motion" if state else "hold",
                        "start": round(start / FPS, 2), "end": round(i / FPS, 2)})
            start, state = i, bool(moving[i])
    out.append({"kind": "motion" if state else "hold",
                "start": round(start / FPS, 2), "end": round(len(moving) / FPS, 2)})
    for seg in out:
        seg["dur"] = round(seg["end"] - seg["start"], 2)
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    crop = sys.argv[2] if len(sys.argv) > 2 else None
    segs = segments(sample(path, crop))
    holds = [s for s in segs if s["kind"] == "hold" and s["dur"] >= 1.0]
    print(json.dumps({"segments": segs, "holds": holds}, indent=1))
