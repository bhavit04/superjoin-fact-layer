"""Maintain a controlled vocabulary of metric names, incrementally.

Lexical similarity will never match "CPI inflation" to "consumer price
inflation". That judgement goes to a model — once per distinct label, not once
per fact pair, so it costs one or two calls per document rather than thousands.
"""
from __future__ import annotations

import re

from .db import Store
from .llm import LLMClient, LLMError
from .normalize import metrics
from .prompts import CLUSTER_SYSTEM

MAX_LABELS_PER_CALL = 60


async def assign_clusters(
    store: Store, client: LLMClient, new_labels: list[str], doc_id: str = ""
) -> dict[str, str]:
    """Map new metric labels to canonical names, falling back to lexical
    matching when no model is reachable."""
    new_labels = [l for l in dict.fromkeys(l.strip() for l in new_labels if l and l.strip())]
    if not new_labels:
        return {}

    existing = _existing_vocabulary(store)
    assignments: dict[str, str] = {}

    for start in range(0, len(new_labels), MAX_LABELS_PER_CALL):
        batch = new_labels[start : start + MAX_LABELS_PER_CALL]
        batch_assignments = await _assign_batch(client, batch, existing)
        assignments.update(batch_assignments)
        # Later batches can attach to names coined by earlier ones.
        existing = sorted(set(existing) | set(batch_assignments.values()))

    for label, canonical in assignments.items():
        store.set_schema_canonical("metric", metrics.metric_key(label), canonical)
    return assignments


def _existing_vocabulary(store: Store) -> list[str]:
    rows = store.schema_snapshot("metric")
    return sorted({(r.get("canonical") or r["key"]).strip() for r in rows if (r.get("canonical") or r.get("key"))})


async def _assign_batch(client: LLMClient, batch: list[str], existing: list[str]) -> dict[str, str]:
    prompt_parts = []
    if existing:
        shown = existing[:400]
        prompt_parts.append("EXISTING canonical metric names:\n" + "\n".join(f"- {name}" for name in shown))
        if len(existing) > len(shown):
            prompt_parts.append(f"({len(existing) - len(shown)} more not shown.)")
    else:
        prompt_parts.append("EXISTING canonical metric names: (none yet -- this is the first document)")
    prompt_parts.append(
        "\nNEW metric labels to assign:\n"
        + "\n".join(f"{i}. {label}" for i, label in enumerate(batch))
    )
    prompt_parts.append("\nReturn only the JSON object, with one assignment per new label.")

    try:
        payload = await client.complete_json(
            system=CLUSTER_SYSTEM,
            prompt="\n".join(prompt_parts),
            task="cluster_metrics",
            max_output_tokens=16384,
        )
    except LLMError as exc:
        # A response cut off by the output budget still contains most of its
        # assignments. Losing the whole batch over a missing closing brace would
        # send every label to the lexical fallback for no reason.
        payload = {"assignments": _salvage_assignments(str(exc))}

    out: dict[str, str] = {}
    items = payload.get("assignments") if isinstance(payload, dict) else payload
    for item in items or []:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index"))
        except (TypeError, ValueError):
            continue
        canonical = str(item.get("canonical") or "").strip().lower()
        if 0 <= index < len(batch) and canonical:
            out[batch[index]] = canonical[:120]

    # Anything the model skipped falls back to lexical matching.
    for label in batch:
        if label not in out:
            out[label] = _lexical_fallback(label, existing)
    return out


_ASSIGNMENT_RE = re.compile(
    r'\{\s*"index"\s*:\s*(\d+)\s*,\s*"canonical"\s*:\s*"([^"]{1,120})"\s*\}'
)


def _salvage_assignments(text: str) -> list[dict]:
    """Recover whole assignment objects from a response that was cut short."""
    return [
        {"index": int(index), "canonical": canonical}
        for index, canonical in _ASSIGNMENT_RE.findall(text or "")
    ]


def _lexical_fallback(label: str, existing: list[str], threshold: float = 0.72) -> str:
    """Closest existing canonical name, or the label itself. The threshold is
    high: over-merging invents contradictions that are not in the documents."""
    best_name, best_score = label.strip().lower(), 0.0
    for name in existing:
        score = metrics.metric_similarity(label, name)
        if score > best_score:
            best_name, best_score = name, score
    return best_name if best_score >= threshold else label.strip().lower()
