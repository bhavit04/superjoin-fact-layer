"""SQLite storage for the knowledge layer.

SQLite rather than a graph database on purpose. The interesting work in this
problem is normalization and adjudication, not traversal; the queries this system
actually runs are "facts sharing a metric cluster and entity" and "relations
touching this fact", both of which are ordinary indexed lookups. A single file
with no server also makes the whole thing clone-and-run for a reviewer.

Everything is additive. Ingesting a document never rewrites existing facts or
relations, which is what makes incremental ingestion cheap.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS documents (
    id             TEXT PRIMARY KEY,
    sha256         TEXT UNIQUE NOT NULL,
    filename       TEXT NOT NULL,
    title          TEXT,
    n_pages        INTEGER,
    n_chunks       INTEGER,
    primary_entity TEXT,
    source_path    TEXT,
    status         TEXT DEFAULT 'pending',
    error          TEXT,
    ingested_at    REAL,
    duration_s     REAL,
    meta_json      TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS facts (
    id               TEXT PRIMARY KEY,
    doc_id           TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_ordinal    INTEGER,

    subject_raw      TEXT,
    subject_key      TEXT,
    metric_raw       TEXT,
    metric_key       TEXT,
    metric_cluster   TEXT,
    derivative_kind  TEXT,

    fact_type        TEXT,          -- numeric | categorical | temporal | textual
    polarity         TEXT,          -- affirmed | negated
    value_raw        TEXT,
    value_text       TEXT,
    value_num        REAL,
    value_low        REAL,
    value_high       REAL,
    value_unit       TEXT,
    value_kind       TEXT,
    is_range         INTEGER DEFAULT 0,
    is_approximate   INTEGER DEFAULT 0,

    qualifiers_json  TEXT DEFAULT '{}',
    period_label     TEXT,
    period_canonical TEXT,
    period_kind      TEXT,
    period_start     TEXT,
    period_end       TEXT,
    period_is_point  INTEGER DEFAULT 0,

    evidence_text    TEXT,
    page             INTEGER,
    page_label       TEXT,
    bbox_json        TEXT DEFAULT '[]',
    match_ratio      REAL,
    grounding_mode   TEXT DEFAULT 'verbatim',
    metric_support   REAL DEFAULT 1.0,
    grounded         INTEGER DEFAULT 0,

    confidence       REAL,
    extractor        TEXT,
    created_at       REAL
);

CREATE INDEX IF NOT EXISTS idx_facts_doc      ON facts(doc_id);
CREATE INDEX IF NOT EXISTS idx_facts_subject  ON facts(subject_key);
CREATE INDEX IF NOT EXISTS idx_facts_cluster  ON facts(metric_cluster);
CREATE INDEX IF NOT EXISTS idx_facts_period   ON facts(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_facts_grounded ON facts(grounded);

CREATE TABLE IF NOT EXISTS relations (
    id           TEXT PRIMARY KEY,
    fact_a       TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    fact_b       TEXT NOT NULL REFERENCES facts(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL,     -- CORROBORATES | CONTRADICTS | RECONCILED | RELATED
    score        REAL,
    method       TEXT,              -- deterministic | llm | hybrid
    rationale    TEXT,
    dimension    TEXT,              -- which qualifier explains a reconciled difference
    cross_doc    INTEGER DEFAULT 0,
    detail_json  TEXT DEFAULT '{}',
    created_at   REAL,
    UNIQUE (fact_a, fact_b)
);

CREATE INDEX IF NOT EXISTS idx_rel_a    ON relations(fact_a);
CREATE INDEX IF NOT EXISTS idx_rel_b    ON relations(fact_b);
CREATE INDEX IF NOT EXISTS idx_rel_kind ON relations(kind);

-- The observed schema, accumulated as documents arrive. This is what makes the
-- fact schema "dynamic": nothing declares the set of metrics or qualifier keys
-- up front, they are registered here the first time a document uses them.
CREATE TABLE IF NOT EXISTS schema_registry (
    kind          TEXT NOT NULL,    -- metric | qualifier | unit | entity | fact_type
    key           TEXT NOT NULL,
    canonical     TEXT,
    count         INTEGER DEFAULT 0,
    examples_json TEXT DEFAULT '[]',
    first_doc     TEXT,
    first_seen    REAL,
    PRIMARY KEY (kind, key)
);

-- Facts the system extracted but could not ground. Kept rather than dropped so
-- extraction failures are inspectable instead of invisible.
CREATE TABLE IF NOT EXISTS quarantine (
    id           TEXT PRIMARY KEY,
    doc_id       TEXT,
    reason       TEXT,
    payload_json TEXT,
    created_at   REAL
);

CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id     TEXT,
    stage      TEXT,
    message    TEXT,
    detail_json TEXT DEFAULT '{}',
    created_at REAL
);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Store:
    """Thread-safe-enough SQLite wrapper: one connection per thread."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = self.conn
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # --- generic helpers -----------------------------------------------------

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, tuple(params)).fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute(sql, tuple(params))

    def executemany(self, sql: str, rows: list[tuple]) -> None:
        if not rows:
            return
        with self._write_lock, self.connect() as conn:
            conn.executemany(sql, rows)

    # --- documents -----------------------------------------------------------

    def find_document_by_hash(self, sha256: str) -> dict | None:
        return self.one("SELECT * FROM documents WHERE sha256 = ?", (sha256,))

    def insert_document(self, **fields) -> str:
        fields.setdefault("id", new_id("doc"))
        fields.setdefault("ingested_at", time.time())
        fields.setdefault("meta_json", "{}")
        cols = ", ".join(fields)
        marks = ", ".join("?" for _ in fields)
        self.execute(f"INSERT INTO documents ({cols}) VALUES ({marks})", tuple(fields.values()))
        return fields["id"]

    def update_document(self, doc_id: str, **fields) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.execute(f"UPDATE documents SET {sets} WHERE id = ?", (*fields.values(), doc_id))

    def delete_document(self, doc_id: str) -> None:
        self.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    # --- facts ---------------------------------------------------------------

    FACT_COLUMNS = [
        "id", "doc_id", "chunk_ordinal", "subject_raw", "subject_key", "metric_raw",
        "metric_key", "metric_cluster", "derivative_kind", "fact_type", "polarity",
        "value_raw", "value_text", "value_num", "value_low", "value_high", "value_unit",
        "value_kind", "is_range", "is_approximate", "qualifiers_json", "period_label",
        "period_canonical", "period_kind", "period_start", "period_end", "period_is_point",
        "evidence_text", "page", "page_label", "bbox_json", "match_ratio", "grounding_mode",
        "metric_support", "grounded",
        "confidence", "extractor", "created_at",
    ]

    def insert_facts(self, facts: list[dict]) -> None:
        rows = [tuple(f.get(c) for c in self.FACT_COLUMNS) for f in facts]
        marks = ", ".join("?" for _ in self.FACT_COLUMNS)
        self.executemany(
            f"INSERT OR REPLACE INTO facts ({', '.join(self.FACT_COLUMNS)}) VALUES ({marks})", rows
        )

    def facts_for_doc(self, doc_id: str) -> list[dict]:
        return self.query("SELECT * FROM facts WHERE doc_id = ?", (doc_id,))

    def all_facts(self, grounded_only: bool = True) -> list[dict]:
        sql = "SELECT * FROM facts"
        if grounded_only:
            sql += " WHERE grounded = 1"
        return self.query(sql)

    def get_fact(self, fact_id: str) -> dict | None:
        return self.one("SELECT * FROM facts WHERE id = ?", (fact_id,))

    # --- relations -----------------------------------------------------------

    def insert_relations(self, relations: list[dict]) -> int:
        if not relations:
            return 0
        cols = ["id", "fact_a", "fact_b", "kind", "score", "method", "rationale",
                "dimension", "cross_doc", "detail_json", "created_at"]
        rows = [tuple(r.get(c) for c in cols) for r in relations]
        marks = ", ".join("?" for _ in cols)
        with self._write_lock, self.connect() as conn:
            before = conn.total_changes
            conn.executemany(
                f"INSERT OR IGNORE INTO relations ({', '.join(cols)}) VALUES ({marks})", rows
            )
            return conn.total_changes - before

    def relations_for_fact(self, fact_id: str) -> list[dict]:
        return self.query(
            "SELECT * FROM relations WHERE fact_a = ? OR fact_b = ?", (fact_id, fact_id)
        )

    # --- schema registry -----------------------------------------------------

    def register_schema(self, kind: str, key: str, example: str = "", doc_id: str = "") -> None:
        if not key:
            return
        with self._write_lock, self.connect() as conn:
            row = conn.execute(
                "SELECT count, examples_json FROM schema_registry WHERE kind = ? AND key = ?",
                (kind, key),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO schema_registry (kind, key, canonical, count, examples_json, first_doc, first_seen)"
                    " VALUES (?, ?, ?, 1, ?, ?, ?)",
                    (kind, key, (example or key).strip().lower()[:120],
                     json.dumps([example] if example else []), doc_id, time.time()),
                )
            else:
                examples = json.loads(row["examples_json"] or "[]")
                if example and example not in examples and len(examples) < 6:
                    examples.append(example)
                conn.execute(
                    "UPDATE schema_registry SET count = count + 1, examples_json = ? WHERE kind = ? AND key = ?",
                    (json.dumps(examples), kind, key),
                )

    def set_schema_canonical(self, kind: str, key: str, canonical: str) -> None:
        self.execute(
            "UPDATE schema_registry SET canonical = ? WHERE kind = ? AND key = ?", (canonical, kind, key)
        )

    def schema_snapshot(self, kind: str | None = None) -> list[dict]:
        if kind:
            return self.query(
                "SELECT * FROM schema_registry WHERE kind = ? ORDER BY count DESC", (kind,)
            )
        return self.query("SELECT * FROM schema_registry ORDER BY kind, count DESC")

    # --- diagnostics ---------------------------------------------------------

    def quarantine_fact(self, doc_id: str, reason: str, payload: dict) -> None:
        self.execute(
            "INSERT INTO quarantine (id, doc_id, reason, payload_json, created_at) VALUES (?,?,?,?,?)",
            (new_id("q"), doc_id, reason, json.dumps(payload, default=str)[:8000], time.time()),
        )

    def log_event(self, doc_id: str, stage: str, message: str, detail: dict | None = None) -> None:
        self.execute(
            "INSERT INTO events (doc_id, stage, message, detail_json, created_at) VALUES (?,?,?,?,?)",
            (doc_id, stage, message, json.dumps(detail or {}, default=str)[:8000], time.time()),
        )

    def stats(self) -> dict:
        def scalar(sql: str, params: tuple = ()) -> int:
            row = self.conn.execute(sql, params).fetchone()
            return int(row[0]) if row and row[0] is not None else 0

        kinds = {
            r["kind"]: r["n"]
            for r in self.query("SELECT kind, COUNT(*) AS n FROM relations GROUP BY kind")
        }
        return {
            "documents": scalar("SELECT COUNT(*) FROM documents WHERE status='ready'"),
            "facts": scalar("SELECT COUNT(*) FROM facts"),
            "facts_grounded": scalar("SELECT COUNT(*) FROM facts WHERE grounded=1"),
            "relations": scalar("SELECT COUNT(*) FROM relations"),
            "relations_cross_doc": scalar("SELECT COUNT(*) FROM relations WHERE cross_doc=1"),
            "by_kind": kinds,
            "quarantined": scalar("SELECT COUNT(*) FROM quarantine"),
            "distinct_metrics": scalar("SELECT COUNT(*) FROM schema_registry WHERE kind='metric'"),
            "distinct_qualifiers": scalar("SELECT COUNT(*) FROM schema_registry WHERE kind='qualifier'"),
            "distinct_entities": scalar("SELECT COUNT(DISTINCT subject_key) FROM facts"),
        }
