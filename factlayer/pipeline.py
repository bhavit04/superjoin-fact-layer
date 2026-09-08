"""Ingestion and linking orchestration.

The shape of ``ingest`` is deliberate:

* Documents are content-addressed, so re-uploading the same PDF is a no-op.
* Extraction runs over chunks concurrently, bounded by the LLM client's semaphore.
* The document's own primary entity is inferred *after* extraction, from what the
  extractor actually saw, then used to resolve "the Company"-style references.
* Linking probes only the NEW facts against the index of everything already
  stored. Existing relations are never recomputed, so ingesting the seventh
  document costs about what ingesting the second did.
* Only pairs the deterministic rules could not settle reach a model, ranked so
  the most consequential ones are spent first when a budget is in force.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from .cluster import assign_clusters
from .config import Settings, get_settings
from .db import Store, new_id
from .extract import extract_chunk, heuristic_extract, normalize_fact
from .index import Candidate, FactIndex, generate_pairs
from .llm import LLMClient, LLMUnavailable
from .normalize import entities, metrics, periods, units
from .pdf import PdfDocument, file_sha256
from .reconcile import (
    CONTRADICTS, CORROBORATES, RECONCILED, RELATED, UNRELATED,
    Observation, Verdict, adjudicate, classify, enumeration_key, find_enumerations, observe,
)

ProgressFn = Callable[[str, str, dict], None]

# How many escalated pairs may reach a model per ingest. Bounded so a large
# document cannot silently spend an unbounded amount of time or quota.
DEFAULT_ADJUDICATION_BUDGET = 140


@dataclass
class IngestResult:
    doc_id: str
    filename: str
    title: str
    pages: int
    chunks: int
    facts_proposed: int = 0
    facts_stored: int = 0
    facts_grounded: int = 0
    quarantined: int = 0
    quarantine_reasons: dict[str, int] = field(default_factory=dict)
    pairs_considered: int = 0
    relations_written: int = 0
    adjudicated: int = 0
    overturned: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    duration_s: float = 0.0
    degraded: bool = False
    notes: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


async def ingest(
    store: Store,
    path: str | Path,
    *,
    filename: str | None = None,
    settings: Settings | None = None,
    progress: ProgressFn | None = None,
    adjudication_budget: int = DEFAULT_ADJUDICATION_BUDGET,
) -> IngestResult:
    settings = settings or get_settings()
    path = Path(path)
    filename = filename or path.name
    started = time.time()

    def emit(stage: str, message: str, **detail) -> None:
        if progress:
            try:
                progress(stage, message, detail)
            except Exception:
                pass

    digest = file_sha256(path)
    existing = store.find_document_by_hash(digest)
    if existing and existing.get("status") == "ready":
        emit("skip", f"{filename} is already in the knowledge layer")
        return IngestResult(
            doc_id=existing["id"], filename=existing["filename"], title=existing.get("title") or "",
            pages=existing.get("n_pages") or 0, chunks=existing.get("n_chunks") or 0,
            facts_stored=len(store.facts_for_doc(existing["id"])),
            notes=["Document already ingested (identical content hash); nothing recomputed."],
        )
    if existing:
        store.delete_document(existing["id"])  # a previous attempt failed; start clean

    doc_id = ""
    pdf = PdfDocument(path)
    try:
        title = pdf.title_guess()
        chunks = pdf.chunks(settings.pages_per_chunk, settings.chunk_char_budget)
        doc_id = store.insert_document(
            sha256=digest, filename=filename, title=title, n_pages=pdf.page_count,
            n_chunks=len(chunks), source_path=str(path), status="extracting",
        )
        result = IngestResult(doc_id=doc_id, filename=filename, title=title,
                              pages=pdf.page_count, chunks=len(chunks))
        emit("start", f"{filename}: {pdf.page_count} pages, {len(chunks)} chunks", doc_id=doc_id)

        async with LLMClient(settings) as client:
            # --- extraction -------------------------------------------------
            raw_facts = await _extract_all(client, chunks, title, emit, result)
            result.facts_proposed = sum(len(items) for items in raw_facts.values())
            emit("extracted", f"{result.facts_proposed} facts proposed", doc_id=doc_id)

            # --- resolve the document's own subject --------------------------
            subjects = [f.get("subject") for items in raw_facts.values() for f in items]
            front_matter = " ".join(pdf.page_text(p) for p in range(1, min(3, pdf.page_count) + 1))
            primary_entity = entities.infer_primary_entity(
                [s for s in subjects if isinstance(s, str)], front_matter=front_matter, title=title,
            )
            if primary_entity:
                emit("entity", f"primary entity resolved to “{primary_entity}”", doc_id=doc_id)

            # --- grounding ---------------------------------------------------
            # A document's fiscal-year convention is a property of the document.
            # Read it from how the document names its own year end, so a filing
            # with a December year end is not silently shifted by a quarter.
            fy_start = periods.detect_fiscal_year_start(front_matter + " " + chunks[0].text)
            if fy_start != periods.FY_START_MONTH:
                emit("calendar", f"fiscal year detected as starting in month {fy_start}", doc_id=doc_id)

            stored = _ground_and_store(
                store, pdf, chunks, raw_facts, doc_id, primary_entity, result, fy_start
            )
            store.update_document(doc_id, primary_entity=primary_entity or "", status="clustering",
                                  meta_json=json.dumps({"fiscal_year_start_month": fy_start}))
            emit("grounded",
                 f"{result.facts_stored} facts grounded, {result.quarantined} quarantined",
                 doc_id=doc_id)

            if not stored:
                store.update_document(doc_id, status="ready", duration_s=time.time() - started)
                result.duration_s = time.time() - started
                # Distinguish "this document yielded nothing" from "we never got to
                # look at it". Reporting an exhausted quota as an empty document
                # sends the reader hunting for a problem in their PDF.
                quota_failures = [f for f in client.failures if "quota" in f["error"].lower()
                                  or "429" in f["error"] or "too_many_requests" in f["error"].lower()]
                if quota_failures or client.exhausted:
                    result.notes.append(
                        f"Extraction could not run: the provider's quota was exhausted "
                        f"({len(quota_failures)} rejected call(s)). Nothing was extracted from this "
                        f"document. Re-run when quota resets, or set a key for another provider -- "
                        f"already-cached responses are unaffected."
                    )
                elif client.failures:
                    result.notes.append(
                        f"Extraction failed on every chunk ({len(client.failures)} error(s)); "
                        f"first was: {client.failures[0]['error'][:160]}"
                    )
                else:
                    result.notes.append("No groundable facts were extracted from this document.")
                result.usage = client.usage.to_dict()
                return result

            # --- metric vocabulary -------------------------------------------
            await _apply_clusters(store, client, stored, doc_id, emit)

            # --- linking ------------------------------------------------------
            store.update_document(doc_id, status="linking")
            await _link(store, client, stored, doc_id, settings, adjudication_budget, emit, result)

            result.usage = client.usage.to_dict()
            result.degraded = not client.available and client.usage.cache_hits == 0
            if result.degraded:
                result.notes.append(
                    "Ran without a reachable model: facts came from the heuristic extractor and "
                    "relations from deterministic rules only."
                )

        result.duration_s = round(time.time() - started, 2)
        store.update_document(doc_id, status="ready", duration_s=result.duration_s)
        store.log_event(doc_id, "ingest", "completed", result.to_dict())
        emit("done", f"{filename}: {result.facts_stored} facts, {result.relations_written} relations",
             doc_id=doc_id, **{"duration_s": result.duration_s})
        return result
    except Exception as exc:
        # doc_id is empty when the PDF could not be opened or chunked at all, in
        # which case there is no row to mark failed.
        if doc_id:
            try:
                store.update_document(doc_id, status="failed", error=str(exc)[:500])
                store.log_event(doc_id, "ingest", "failed", {"error": str(exc)[:500]})
            except Exception:
                pass
        raise
    finally:
        pdf.close()


def renormalize(store: Store, progress: ProgressFn | None = None) -> dict[str, int]:
    """Re-parse stored values and periods in place, without re-reading any PDF.

    Values are normalized at ingest and then frozen in the database, so a fix to
    the unit or period parser previously required re-extracting an entire corpus
    to take effect -- paying again for the one stage that had not changed. This
    re-derives just the parsed columns from the raw text already stored.
    """
    facts = store.all_facts(grounded_only=False)
    updates, changed = [], 0
    for fact in facts:
        try:
            qualifiers = json.loads(fact.get("qualifiers_json") or "{}")
        except (TypeError, ValueError):
            qualifiers = {}
        fy_start = None
        meta = store.one("SELECT meta_json FROM documents WHERE id = ?", (fact["doc_id"],))
        if meta:
            try:
                fy_start = json.loads(meta.get("meta_json") or "{}").get("fiscal_year_start_month")
            except (TypeError, ValueError):
                fy_start = None

        value = units.parse_value(fact.get("value_raw") or "", unit_hint=qualifiers.get("unit_hint"))
        # Re-parse from the period text the document actually gave, not from the
        # span a previous parser matched inside it: "April to December 2024" was
        # stored with the label "December 2024", and re-reading the label could
        # never recover the nine months the document meant.
        period_text = qualifiers.get("period") or fact.get("period_label") or ""
        period = periods.parse_period(period_text, fy_start)
        if (value.number != fact.get("value_num")) or (period.start != fact.get("period_start")):
            changed += 1
        updates.append((
            value.number, value.low, value.high, value.unit or fact.get("value_unit"),
            value.kind or fact.get("value_kind"), int(value.is_range), int(value.is_approximate),
            period.canonical or fact.get("period_canonical"), period.kind or fact.get("period_kind"),
            period.start, period.end, int(period.is_point),
            period.label or fact.get("period_label"), fact["id"],
        ))

    store.executemany(
        "UPDATE facts SET value_num=?, value_low=?, value_high=?, value_unit=?, value_kind=?, "
        "is_range=?, is_approximate=?, period_canonical=?, period_kind=?, period_start=?, "
        "period_end=?, period_is_point=?, period_label=? WHERE id=?", updates)
    if progress:
        progress("renormalize", f"re-parsed {len(facts)} facts, {changed} changed", {})
    return {"facts": len(facts), "changed": changed}


async def relink(
    store: Store,
    *,
    settings: Settings | None = None,
    adjudication_budget: int = 60,
    progress: ProgressFn | None = None,
) -> IngestResult:
    """Recompute every relation from facts already stored, without re-extracting.

    Extraction is the expensive stage and its output does not change when the
    comparison logic does. Rebuilding a whole corpus to pick up a change in how
    two facts are judged wastes that work; this re-derives only the stage that
    actually changed, which takes seconds instead of half an hour.
    """
    settings = settings or get_settings()
    started = time.time()
    result = IngestResult(doc_id="", filename="(all documents)", title="", pages=0, chunks=0)

    def emit(stage: str, message: str, **detail) -> None:
        if progress:
            try:
                progress(stage, message, detail)
            except Exception:
                pass

    facts = store.all_facts(grounded_only=False)
    result.facts_stored = len(facts)
    emit("relink", f"re-deriving relations for {len(facts)} stored facts")
    store.execute("DELETE FROM relations")

    async with LLMClient(settings) as client:
        await _link(store, client, facts, "", settings, adjudication_budget, emit, result)
        result.usage = client.usage.to_dict()

    result.duration_s = round(time.time() - started, 2)
    emit("done", f"{result.relations_written} relations rebuilt in {result.duration_s}s")
    return result


# --- stages ------------------------------------------------------------------

async def _extract_all(
    client: LLMClient, chunks: Sequence, title: str, emit, result: IngestResult
) -> dict[int, list[dict]]:
    """Extract every chunk concurrently; fall back to heuristics per chunk."""
    done = 0
    total = len(chunks)

    allow_heuristic = getattr(client.settings, "allow_heuristic_fallback", True)

    def _degraded(chunk) -> list[dict]:
        if not allow_heuristic:
            emit("warn", f"no cached response for chunk {chunk.ordinal} "
                         f"(pages {chunk.page_start}-{chunk.page_end}); skipping")
            result.notes.append(
                f"Chunk {chunk.ordinal} had no cached response and was skipped "
                "(replay mode does not substitute heuristic facts)."
            )
            return []
        return [{**f, "_extractor": "heuristic"} for f in heuristic_extract(chunk)]

    async def one(chunk) -> tuple[int, list[dict]]:
        nonlocal done
        try:
            facts = await extract_chunk(client, chunk, title)
            for fact in facts:
                fact["_extractor"] = "llm"
            if not facts and not client.available:
                facts = _degraded(chunk)
        except LLMUnavailable:
            facts = _degraded(chunk)
        except Exception as exc:
            emit("warn", f"chunk {chunk.ordinal} (pages {chunk.page_start}-{chunk.page_end}) failed: {exc}")
            result.notes.append(f"Chunk {chunk.ordinal} failed during extraction: {exc}")
            facts = []
        done += 1
        if done % 5 == 0 or done == total:
            emit("progress", f"extracted {done}/{total} chunks")
        return chunk.ordinal, facts

    pairs = await asyncio.gather(*(one(c) for c in chunks))
    return dict(pairs)


def _ground_and_store(
    store: Store, pdf: PdfDocument, chunks: Sequence, raw_facts: dict[int, list[dict]],
    doc_id: str, primary_entity: str | None, result: IngestResult, fy_start: int | None = None,
) -> list[dict]:
    by_ordinal = {c.ordinal: c for c in chunks}
    rows: list[dict] = []
    seen: set[tuple] = set()

    for ordinal, items in raw_facts.items():
        chunk = by_ordinal.get(ordinal)
        if chunk is None:
            continue
        for raw in items:
            extractor = raw.get("_extractor", "llm")
            row, reason = normalize_fact(
                raw, doc_id=doc_id, chunk=chunk, pdf=pdf,
                primary_entity=primary_entity, extractor=extractor, fy_start=fy_start,
            )
            if row is None:
                result.quarantined += 1
                result.quarantine_reasons[reason] = result.quarantine_reasons.get(reason, 0) + 1
                store.quarantine_fact(doc_id, reason, raw)
                continue
            # Collapse facts the extractor emitted twice from overlapping chunks.
            key = (row["subject_key"], row["metric_key"], row["value_raw"], row["period_canonical"], row["page"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    store.insert_facts(rows)
    for row in rows:
        store.register_schema("metric", row["metric_key"], row["metric_raw"], doc_id)
        store.register_schema("entity", row["subject_key"], row["subject_raw"], doc_id)
        store.register_schema("fact_type", row["fact_type"], row["metric_raw"], doc_id)
        if row["value_unit"]:
            store.register_schema("unit", row["value_unit"], row["value_raw"], doc_id)
        try:
            for key in json.loads(row["qualifiers_json"]):
                if not key.startswith("_"):
                    store.register_schema("qualifier", key, row["metric_raw"], doc_id)
        except (TypeError, ValueError):
            pass

    result.facts_stored = len(rows)
    result.facts_grounded = sum(1 for r in rows if r["grounded"])
    return rows


async def _apply_clusters(store: Store, client: LLMClient, rows: list[dict], doc_id: str, emit) -> None:
    """Assign this document's new metric labels to the shared vocabulary."""
    known = {r["key"]: (r.get("canonical") or r["key"]) for r in store.schema_snapshot("metric")}
    new_labels: dict[str, str] = {}   # metric_key -> a representative raw label
    for row in rows:
        key = row["metric_key"]
        if known.get(key) in (None, key) and key not in new_labels:
            new_labels[key] = row["metric_raw"]

    assignments: dict[str, str] = {}
    if new_labels:
        try:
            assignments = await assign_clusters(store, client, list(new_labels.values()), doc_id)
        except Exception as exc:
            emit("warn", f"metric clustering unavailable ({exc}); falling back to lexical keys")

    label_to_canonical = {label.strip(): canonical for label, canonical in assignments.items()}
    refreshed = {r["key"]: (r.get("canonical") or r["key"]) for r in store.schema_snapshot("metric")}

    updates: list[tuple[str, str]] = []
    for row in rows:
        canonical = label_to_canonical.get(row["metric_raw"].strip()) or refreshed.get(row["metric_key"])
        cluster = metrics.metric_key(canonical) if canonical else row["metric_key"]
        if cluster and cluster != row["metric_cluster"]:
            row["metric_cluster"] = cluster
            updates.append((cluster, row["id"]))
    if updates:
        store.executemany("UPDATE facts SET metric_cluster = ? WHERE id = ?", updates)
    emit("clustered", f"{len(new_labels)} new metric labels folded into the vocabulary")


async def _link(
    store: Store, client: LLMClient, new_rows: list[dict], doc_id: str,
    settings: Settings, budget: int, emit, result: IngestResult,
) -> None:
    all_facts = store.all_facts(grounded_only=False)
    index = FactIndex(all_facts)
    by_id = {f["id"]: f for f in all_facts}
    probes = [by_id.get(r["id"], r) for r in new_rows if r["id"] in by_id or r]

    candidates = generate_pairs(index, probes, settings.candidate_top_k, settings.metric_sim_threshold)
    result.pairs_considered = len(candidates)
    enumerations = find_enumerations(all_facts)
    emit("candidates", f"{len(candidates)} candidate pairs from {len(all_facts)} facts")

    titles = {d["id"]: (d.get("title") or d.get("filename") or "") for d in store.query("SELECT id, title, filename FROM documents")}

    settled: list[tuple[Candidate, Observation, Verdict]] = []
    escalate: list[tuple[Candidate, Observation, Verdict]] = []
    for candidate in candidates:
        obs = observe(candidate.fact_a, candidate.fact_b, candidate.similarity, candidate.same_cluster)
        verdict = classify(candidate.fact_a, candidate.fact_b, obs)
        if verdict.kind == UNRELATED:
            continue
        # Repeated rows of one table are a list of events, not rival claims.
        key = enumeration_key(candidate.fact_a)
        if key in enumerations and key == enumeration_key(candidate.fact_b):
            verdict = Verdict(
                RELATED, 0.3, "deterministic",
                "This subject, metric and period carry several different values in the same "
                "document, so these are entries in a series -- such as separate allotments or "
                "transactions -- rather than competing claims about one quantity.",
                dimension="enumeration",
            )
        (escalate if verdict.needs_llm else settled).append((candidate, obs, verdict))

    # Spend the adjudication budget where it changes the answer most: genuine
    # conflicts first, then cross-document pairs, then everything else.
    def priority(item) -> tuple:
        candidate, obs, verdict = item
        kind_rank = {CONTRADICTS: 0, RECONCILED: 1, CORROBORATES: 2, RELATED: 3}.get(verdict.kind, 4)
        return (kind_rank, 0 if not obs.same_document else 1, -obs.metric_similarity)

    escalate.sort(key=priority)
    chosen, deferred = escalate[:budget], escalate[budget:]
    if deferred:
        result.notes.append(
            f"{len(deferred)} ambiguous pairs kept their rule-based verdict because the "
            f"adjudication budget of {budget} was reached."
        )

    if chosen:
        emit("adjudicate", f"sending {len(chosen)} ambiguous pairs for adjudication")

        async def judge(item):
            candidate, obs, verdict = item
            try:
                final = await adjudicate(client, candidate.fact_a, candidate.fact_b, obs, verdict, titles)
            except Exception:
                final = verdict
            return candidate, obs, final

        judged = await asyncio.gather(*(judge(i) for i in chosen))
        result.adjudicated = sum(1 for _, _, v in judged if v.detail.get("adjudicated"))
        result.overturned = sum(1 for _, _, v in judged if v.detail.get("overturned"))
    else:
        judged = []

    final_rows: list[dict] = []
    for candidate, obs, verdict in list(settled) + list(judged) + deferred:
        if verdict.kind == UNRELATED:
            continue
        result.by_kind[verdict.kind] = result.by_kind.get(verdict.kind, 0) + 1
        final_rows.append({
            "id": new_id("rel"),
            "fact_a": candidate.fact_a["id"],
            "fact_b": candidate.fact_b["id"],
            "kind": verdict.kind,
            "score": verdict.score,
            "method": verdict.method,
            "rationale": verdict.rationale[:2000],
            "dimension": verdict.dimension,
            "cross_doc": int(candidate.fact_a["doc_id"] != candidate.fact_b["doc_id"]),
            "detail_json": json.dumps({"observation": obs.to_dict(), **verdict.detail}, default=str)[:12000],
            "created_at": time.time(),
        })

    result.relations_written = store.insert_relations(final_rows)
    emit("linked", f"{result.relations_written} relations written", **result.by_kind)
