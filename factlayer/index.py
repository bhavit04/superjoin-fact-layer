"""Decide which fact pairs are worth comparing at all.

All-pairs is O(n²) — 4.8M pairs at 3,100 facts. An IDF-weighted inverted index
over metric tokens plus an entity check narrows that to a bounded top-K per fact,
which keeps pair generation roughly linear and makes incremental ingest cheap.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

from .normalize import entities, metrics


@dataclass
class Candidate:
    fact_a: dict
    fact_b: dict
    similarity: float
    same_cluster: bool


class FactIndex:
    """An inverted index over metric tokens, built once per linking pass."""

    def __init__(self, facts: Sequence[dict]):
        self.facts: dict[str, dict] = {f["id"]: f for f in facts}
        self.postings: dict[str, list[str]] = defaultdict(list)
        self.tokens: dict[str, set[str]] = {}
        self.by_cluster: dict[str, list[str]] = defaultdict(list)

        for fact in facts:
            toks = set(metrics.metric_tokens(fact.get("metric_raw"))) or {"_untitled"}
            self.tokens[fact["id"]] = toks
            for token in toks:
                self.postings[token].append(fact["id"])
            self.by_cluster[fact.get("metric_cluster") or ""].append(fact["id"])

        total = max(1, len(facts))
        self.idf = {
            token: math.log(1.0 + total / len(ids)) for token, ids in self.postings.items()
        }

    def __len__(self) -> int:
        return len(self.facts)

    def add(self, facts: Iterable[dict]) -> None:
        """Extend in place, for linking a new document against what is stored."""
        for fact in facts:
            if fact["id"] in self.facts:
                continue
            self.facts[fact["id"]] = fact
            toks = set(metrics.metric_tokens(fact.get("metric_raw"))) or {"_untitled"}
            self.tokens[fact["id"]] = toks
            for token in toks:
                self.postings[token].append(fact["id"])
            self.by_cluster[fact.get("metric_cluster") or ""].append(fact["id"])
        total = max(1, len(self.facts))
        self.idf = {
            token: math.log(1.0 + total / len(ids)) for token, ids in self.postings.items()
        }

    def neighbours(self, fact: dict, top_k: int, min_similarity: float) -> list[Candidate]:
        """The strongest ``top_k`` comparable facts for ``fact``."""
        fact_id = fact["id"]
        my_tokens = self.tokens.get(fact_id) or set(metrics.metric_tokens(fact.get("metric_raw")))
        if not my_tokens:
            return []

        # Stage 1: cheap IDF overlap. Very common tokens are skipped entirely
        # unless the metric is made only of common tokens.
        scores: dict[str, float] = defaultdict(float)
        rare_tokens = [t for t in my_tokens if self.idf.get(t, 0.0) > 0.35]
        for token in (rare_tokens or list(my_tokens)):
            postings = self.postings.get(token, ())
            if len(postings) > 4000:
                continue
            weight = self.idf.get(token, 0.0)
            for other_id in postings:
                if other_id != fact_id:
                    scores[other_id] += weight

        # Facts assigned to the same metric cluster are always considered, even if
        # they share no surface tokens ("CPI inflation" vs "consumer price inflation").
        for other_id in self.by_cluster.get(fact.get("metric_cluster") or "", ()):
            if other_id != fact_id:
                scores[other_id] += 10.0

        if not scores:
            return []

        shortlist = sorted(scores.items(), key=lambda kv: -kv[1])[: max(top_k * 6, 60)]

        # Stage 2: full scoring on the shortlist only.
        out: list[Candidate] = []
        subject_key = fact.get("subject_key") or ""
        my_cluster = fact.get("metric_cluster") or ""
        for other_id, _ in shortlist:
            other = self.facts[other_id]
            if not entities.entities_match(subject_key, other.get("subject_key") or ""):
                continue
            same_cluster = bool(my_cluster) and my_cluster == (other.get("metric_cluster") or "")
            # Two facts are only the same claim if a model put their metrics in one
            # cluster, or their metric names are token-for-token equivalent.
            # Mere similarity is not enough -- see metrics.same_quantity.
            comparable = same_cluster or metrics.same_quantity(
                fact.get("metric_raw"), other.get("metric_raw")
            )
            if not comparable:
                continue
            similarity = 1.0 if same_cluster else metrics.metric_similarity(
                fact.get("metric_raw"), other.get("metric_raw")
            )
            if similarity < min_similarity:
                continue
            out.append(Candidate(fact, other, similarity, same_cluster))

        out.sort(key=lambda c: -c.similarity)
        return out[:top_k]


def generate_pairs(
    index: FactIndex,
    probe_facts: Sequence[dict],
    top_k: int,
    min_similarity: float,
) -> list[Candidate]:
    """Unique candidate pairs seeded from `probe_facts`. Probing only new facts
    is what makes ingestion incremental."""
    seen: set[tuple[str, str]] = set()
    pairs: list[Candidate] = []
    for fact in probe_facts:
        for candidate in index.neighbours(fact, top_k, min_similarity):
            a, b = candidate.fact_a["id"], candidate.fact_b["id"]
            key = (a, b) if a < b else (b, a)
            if key in seen:
                continue
            seen.add(key)
            # Order deterministically so relation rows are stable across runs.
            if a > b:
                candidate = Candidate(candidate.fact_b, candidate.fact_a, candidate.similarity, candidate.same_cluster)
            pairs.append(candidate)
    return pairs
