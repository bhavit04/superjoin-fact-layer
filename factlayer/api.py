"""HTTP API and the UI it serves.

Upload PDFs, watch them process, browse facts, evidence and relationships.
`/api/cases` selects the four required cases from live data, not a fixed list.
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .cases import build_cases
from .claims import build_claims, claim_stats
from .config import get_settings
from .db import Store
from .llm import LLMClient
from .pdf import PdfDocument
from .pipeline import ingest

settings = get_settings()
store = Store(settings.db_path)
WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="Fact Knowledge Layer", version="0.1.0")

# --- job tracking ------------------------------------------------------------

JOBS: dict[str, dict[str, Any]] = {}
_JOB_LIMIT = 200


def _new_job(filenames: list[str]) -> str:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "id": job_id, "state": "queued", "files": filenames, "events": [],
        "results": [], "error": None, "started_at": time.time(),
    }
    for stale in list(JOBS)[:-_JOB_LIMIT]:
        JOBS.pop(stale, None)
    return job_id


def _record(job_id: str, stage: str, message: str, detail: dict | None = None) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    job["events"].append({"t": round(time.time() - job["started_at"], 2), "stage": stage,
                          "message": message, "detail": detail or {}})
    job["events"] = job["events"][-400:]


async def _run_job(job_id: str, paths: list[tuple[Path, str]]) -> None:
    job = JOBS[job_id]
    job["state"] = "running"
    try:
        for path, original_name in paths:
            _record(job_id, "file", f"processing {original_name}")
            result = await ingest(
                store, path, filename=original_name, settings=settings,
                progress=lambda stage, message, detail: _record(job_id, stage, message, detail),
            )
            job["results"].append(result.to_dict())
        job["state"] = "done"
    except Exception as exc:  # surfaced to the UI rather than swallowed
        job["state"] = "error"
        job["error"] = f"{type(exc).__name__}: {exc}"
        _record(job_id, "error", str(exc))
    finally:
        job["finished_at"] = time.time()


# --- ingestion ---------------------------------------------------------------

@app.post("/api/documents")
async def upload_documents(background: BackgroundTasks, files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "no files supplied")
    saved: list[tuple[Path, str]] = []
    for upload in files:
        name = Path(upload.filename or "document.pdf").name
        if not name.lower().endswith(".pdf"):
            raise HTTPException(400, f"{name}: only PDF files are accepted")
        target = settings.upload_dir / f"{uuid.uuid4().hex[:8]}_{name}"
        with open(target, "wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        saved.append((target, name))

    job_id = _new_job([n for _, n in saved])
    background.add_task(_run_job, job_id, saved)
    return {"job_id": job_id, "files": [n for _, n in saved]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "unknown job")
    return job


# --- browsing ----------------------------------------------------------------

@app.get("/api/stats")
def get_stats():
    documents = store.query("SELECT * FROM documents ORDER BY ingested_at DESC")
    return {"stats": store.stats(), "documents": documents,
            "llm": LLMClient(settings).describe()}


@app.get("/api/documents")
def list_documents():
    return store.query("SELECT * FROM documents ORDER BY ingested_at DESC")


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    if not store.one("SELECT id FROM documents WHERE id = ?", (doc_id,)):
        raise HTTPException(404, "unknown document")
    store.delete_document(doc_id)
    return {"deleted": doc_id}


@app.get("/api/facts")
def list_facts(
    q: str = "", doc: str = "", fact_type: str = "", subject: str = "",
    grounded: str = "", has_relations: str = "",
    limit: int = Query(60, le=500), offset: int = 0,
):
    where, params = [], []
    if q:
        where.append("(metric_raw LIKE ? OR subject_raw LIKE ? OR value_raw LIKE ? OR evidence_text LIKE ?)")
        params += [f"%{q}%"] * 4
    if doc:
        where.append("doc_id = ?"); params.append(doc)
    if fact_type:
        where.append("fact_type = ?"); params.append(fact_type)
    if subject:
        where.append("subject_key = ?"); params.append(subject)
    if grounded == "1":
        where.append("grounded = 1")
    if has_relations == "1":
        where.append("id IN (SELECT fact_a FROM relations UNION SELECT fact_b FROM relations)")
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    total = store.one(f"SELECT COUNT(*) AS n FROM facts {clause}", params)["n"]
    rows = store.query(
        f"SELECT * FROM facts {clause} ORDER BY confidence DESC, id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    return {"total": total, "facts": [_decorate_fact(r) for r in rows]}


@app.get("/api/facts/{fact_id}")
def get_fact(fact_id: str):
    fact = store.get_fact(fact_id)
    if not fact:
        raise HTTPException(404, "unknown fact")
    rows = store.relations_for_fact(fact_id)
    others = store.get_facts(
        [r["fact_b"] if r["fact_a"] == fact_id else r["fact_a"] for r in rows])
    relations = []
    for relation in rows:
        other_id = relation["fact_b"] if relation["fact_a"] == fact_id else relation["fact_a"]
        other = others.get(other_id)
        if other:
            relations.append({**_decorate_relation(relation), "other": _decorate_fact(other)})
    relations.sort(key=lambda r: (_KIND_ORDER.get(r["kind"], 9), -(r["score"] or 0)))
    return {"fact": _decorate_fact(fact), "relations": relations}


@app.get("/api/facts/{fact_id}/evidence.png")
def fact_evidence_image(fact_id: str, crop: int = 0):
    fact = store.get_fact(fact_id)
    if not fact:
        raise HTTPException(404, "unknown fact")
    document = store.documents_map().get(fact["doc_id"])
    if not document or not document.get("source_path"):
        raise HTTPException(404, "source document is no longer available")
    path = Path(document["source_path"])
    if not path.exists():
        raise HTTPException(404, "source file missing from disk")
    try:
        rects = json.loads(fact.get("bbox_json") or "[]")
    except (TypeError, ValueError):
        rects = []
    with PdfDocument(path) as pdf:
        png = pdf.render_page_png(fact["page"], rects, crop=bool(crop))
    return Response(png, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})


_KIND_ORDER = {"CONTRADICTS": 0, "RECONCILED": 1, "CORROBORATES": 2, "RELATED": 3}


@app.get("/api/relations")
def list_relations(
    kind: str = "", cross_doc: str = "", dimension: str = "",
    method: str = "", q: str = "", limit: int = Query(60, le=500), offset: int = 0,
):
    where, params = [], []
    if kind:
        where.append("r.kind = ?"); params.append(kind)
    if cross_doc == "1":
        where.append("r.cross_doc = 1")
    if dimension:
        where.append("r.dimension = ?"); params.append(dimension)
    if method:
        where.append("r.method = ?"); params.append(method)
    if q:
        where.append("(fa.metric_raw LIKE ? OR fb.metric_raw LIKE ? OR r.rationale LIKE ?)")
        params += [f"%{q}%"] * 3
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    join = ("FROM relations r JOIN facts fa ON fa.id = r.fact_a JOIN facts fb ON fb.id = r.fact_b")

    total = store.one(f"SELECT COUNT(*) AS n {join} {clause}", params)["n"]
    rows = store.query(
        f"SELECT r.* {join} {clause} ORDER BY r.cross_doc DESC, r.score DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    )
    facts = store.get_facts([r["fact_a"] for r in rows] + [r["fact_b"] for r in rows])
    out = []
    for relation in rows:
        a, b = facts.get(relation["fact_a"]), facts.get(relation["fact_b"])
        if a and b:
            out.append({**_decorate_relation(relation), "a": _decorate_fact(a), "b": _decorate_fact(b)})
    return {"total": total, "relations": out}


@app.get("/api/relations/{relation_id}")
def get_relation(relation_id: str):
    relation = store.one("SELECT * FROM relations WHERE id = ?", (relation_id,))
    if not relation:
        raise HTTPException(404, "unknown relation")
    a, b = store.get_fact(relation["fact_a"]), store.get_fact(relation["fact_b"])
    return {**_decorate_relation(relation), "a": _decorate_fact(a), "b": _decorate_fact(b)}


@app.get("/api/schema")
def get_schema():
    """The schema as accumulated from documents, not as declared."""
    snapshot = store.schema_snapshot()
    grouped: dict[str, list[dict]] = {}
    for row in snapshot:
        try:
            row["examples"] = json.loads(row.pop("examples_json") or "[]")
        except (TypeError, ValueError):
            row["examples"] = []
        grouped.setdefault(row["kind"], []).append(row)
    return grouped


@app.get("/api/quarantine")
def get_quarantine(limit: int = Query(100, le=500)):
    rows = store.query("SELECT * FROM quarantine ORDER BY created_at DESC LIMIT ?", (limit,))
    for row in rows:
        try:
            row["payload"] = json.loads(row.pop("payload_json") or "{}")
        except (TypeError, ValueError):
            row["payload"] = {}
    reasons = store.query("SELECT reason, COUNT(*) AS n FROM quarantine GROUP BY reason ORDER BY n DESC")
    return {"reasons": reasons, "items": rows}


@app.get("/api/claims")
def list_claims(q: str = "", conflicts: str = "", limit: int = Query(60, le=200)):
    """Everything every source says about one quantity, grouped."""
    claims = build_claims(store, limit=limit, only_conflicts=conflicts == "1", query=q)
    return {"stats": claim_stats(claims), "claims": claims}


@app.get("/api/cases")
def get_cases():
    """The four required cases, selected from live data."""
    return build_cases(store)


@app.get("/api/health")
def health():
    client = LLMClient(settings)
    return {
        "ok": True,
        "provider": settings.provider,
        "model": settings.model,
        "live_llm": client.available,
        "cache_entries": client.cache.size(),
        "database": str(settings.db_path),
        "documents": store.stats()["documents"],
    }


# --- shaping -----------------------------------------------------------------

def _decorate_fact(fact: dict | None) -> dict | None:
    if not fact:
        return None
    fact = dict(fact)
    try:
        fact["qualifiers"] = {
            k: v for k, v in json.loads(fact.pop("qualifiers_json") or "{}").items()
            if not k.startswith("_")
        }
    except (TypeError, ValueError):
        fact["qualifiers"] = {}
    try:
        fact["bbox"] = json.loads(fact.pop("bbox_json") or "[]")
    except (TypeError, ValueError):
        fact["bbox"] = []
    document = store.documents_map().get(fact["doc_id"], {})
    fact["doc_filename"] = document.get("filename", "")
    fact["doc_title"] = document.get("title", "")
    return fact


def _decorate_relation(relation: dict) -> dict:
    relation = dict(relation)
    try:
        relation["detail"] = json.loads(relation.pop("detail_json") or "{}")
    except (TypeError, ValueError):
        relation["detail"] = {}
    return relation


# --- UI ----------------------------------------------------------------------

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    page = WEB_DIR / "index.html"
    if not page.exists():
        return HTMLResponse("<h1>Fact Knowledge Layer</h1><p>UI not built. API is at /docs.</p>")
    html = page.read_text(encoding="utf-8")
    # Stamp the asset URLs with each file's mtime. Without this the browser keeps
    # serving a stale app.js after an edit, which is confusing during development
    # and worse during a demo.
    for asset in ("app.js", "style.css"):
        path = WEB_DIR / asset
        if path.exists():
            html = html.replace(f"/static/{asset}", f"/static/{asset}?v={int(path.stat().st_mtime)}")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
