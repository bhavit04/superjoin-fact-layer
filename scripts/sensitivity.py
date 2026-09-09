#!/usr/bin/env python
"""Measure how much the judgement thresholds actually matter.

The cutoffs in `Thresholds` were chosen by inspecting one corpus, which is a fair
thing to be sceptical about. This varies each one across a plausible range,
re-derives every relation, and reports how far the verdict counts move.

A threshold whose verdicts barely shift across its range is not finely tuned. One
that swings the totals is load-bearing and should be treated as a known risk.
Re-linking is sub-second, so the whole sweep runs in about a minute.

    python scripts/sensitivity.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factlayer import config                    # noqa: E402
from factlayer.config import get_settings       # noqa: E402
from factlayer.db import Store                  # noqa: E402
from factlayer.pipeline import relink           # noqa: E402

SWEEPS = {
    "text_equality":     [0.70, 0.76, 0.82, 0.88, 0.94],
    "shared_evidence":   [0.80, 0.85, 0.90, 0.95, 0.99],
    "attribution_floor": [0.10, 0.20, 0.34, 0.50, 0.70],
    "enumeration_min":   [2, 3, 4, 6],
    "scale_window":      [0.05, 0.10, 0.18, 0.30],
}
KINDS = ("CONTRADICTS", "RECONCILED", "CORROBORATES", "RELATED")


def measure(store: Store) -> dict[str, int]:
    settings = get_settings(refresh=True)
    config.refresh_thresholds()
    asyncio.run(relink(store, settings=settings, adjudication_budget=0))
    counts = {r["kind"]: r["n"] for r in
              store.query("SELECT kind, COUNT(*) AS n FROM relations GROUP BY kind")}
    return {k: counts.get(k, 0) for k in KINDS}


def main() -> int:
    os.environ["FACTLAYER_OFFLINE"] = "1"
    store = Store(get_settings().db_path)

    baseline = measure(store)
    print("baseline (deterministic verdicts only)")
    print("   " + "  ".join(f"{k}={v}" for k, v in baseline.items()))

    for name, values in SWEEPS.items():
        env = f"FACTLAYER_T_{name.upper()}"
        print(f"\n{name}")
        swing = 0
        for value in values:
            os.environ[env] = str(value)
            counts = measure(store)
            delta = sum(abs(counts[k] - baseline[k]) for k in KINDS)
            swing = max(swing, delta)
            total = sum(counts.values()) or 1
            marker = "  <- default" if abs(value - _default(name)) < 1e-9 else ""
            print(f"   {value:<6} " + "  ".join(f"{k[:5]}={counts[k]:5}" for k in KINDS)
                  + f"   moved {100 * delta / total:5.1f}%{marker}")
        os.environ.pop(env, None)
        verdict = ("stable — not finely tuned" if swing / max(sum(baseline.values()), 1) < 0.05
                   else "load-bearing — a known risk")
        print(f"   => {verdict}")

    os.environ.pop("FACTLAYER_OFFLINE", None)
    measure(store)      # leave the database on the defaults
    print("\nrestored to defaults")
    return 0


def _default(name: str) -> float:
    return float(getattr(config.Thresholds(), name))


if __name__ == "__main__":
    raise SystemExit(main())
