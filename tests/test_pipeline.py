"""End-to-end ingestion with no API key, exercising the degraded path."""
import asyncio
from pathlib import Path

import pytest

from factlayer.config import Settings
from factlayer.db import Store
from factlayer.pipeline import ingest

CORPUS = Path(__file__).resolve().parent.parent / "data_raw" / "starter-datasets"
SAMPLE = CORPUS / "delhivery" / "03-delhivery-q4-fy24-earnings-presentation.pdf"

pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="starter dataset not present")


@pytest.fixture
def offline(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("FACTLAYER_OFFLINE", "1")
    settings = Settings()
    settings.db_path = tmp_path / "test.db"
    settings.cache_dir = tmp_path / "cache"
    settings.upload_dir = tmp_path / "uploads"
    settings.offline = True
    for directory in (settings.cache_dir, settings.upload_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return settings


def test_ingest_without_a_model_still_produces_grounded_facts(offline):
    store = Store(offline.db_path)
    result = asyncio.run(ingest(store, SAMPLE, settings=offline))
    assert result.facts_stored > 0
    assert result.facts_grounded == result.facts_stored, "every stored fact must be grounded"
    assert result.degraded is True
    assert any("without a reachable model" in note for note in result.notes)
    for fact in store.all_facts(grounded_only=False):
        assert fact["evidence_text"] and fact["page"] >= 1


def test_reingesting_identical_content_is_a_no_op(offline):
    """Content addressing is what makes 'many PDFs in one layer' safe to re-run."""
    store = Store(offline.db_path)
    first = asyncio.run(ingest(store, SAMPLE, settings=offline))
    before = store.stats()
    second = asyncio.run(ingest(store, SAMPLE, settings=offline))
    assert second.doc_id == first.doc_id
    assert store.stats()["facts"] == before["facts"]
    assert any("already ingested" in note for note in second.notes)


def test_the_schema_registry_grows_from_the_document(offline):
    store = Store(offline.db_path)
    asyncio.run(ingest(store, SAMPLE, settings=offline))
    metrics = store.schema_snapshot("metric")
    assert metrics, "metric names must be registered as they are observed"
    assert all(row["count"] >= 1 for row in metrics)
