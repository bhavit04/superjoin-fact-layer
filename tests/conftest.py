import json
import time

import pytest


def make_fact(**overrides):
    """A fact row shaped like the ones the pipeline stores."""
    fact = {
        "id": overrides.pop("id", f"f_{time.time_ns() % 10**9}"),
        "doc_id": "doc_a",
        "subject_raw": "Acme Logistics Limited",
        "subject_key": "acme logistics",
        "metric_raw": "revenue from operations",
        "metric_key": "operation revenue",
        "metric_cluster": "operation revenue",
        "derivative_kind": None,
        "fact_type": "numeric",
        "polarity": "affirmed",
        "value_raw": "8,142",
        "value_num": 8_142_000_000.0,
        "value_low": None,
        "value_high": None,
        "value_unit": "INR",
        "value_kind": "money",
        "is_range": 0,
        "is_approximate": 0,
        "qualifiers_json": "{}",
        "period_label": "FY24",
        "period_canonical": "FY2024",
        "period_kind": "FY",
        "period_start": "2023-04-01",
        "period_end": "2024-03-31",
        "period_is_point": 0,
        "evidence_text": "Revenue from operations for FY24 was Rs. 8,142 Mn",
        "page": 12,
        "match_ratio": 1.0,
        "grounded": 1,
        "confidence": 0.9,
    }
    qualifiers = overrides.pop("qualifiers", None)
    fact.update(overrides)
    if qualifiers is not None:
        fact["qualifiers_json"] = json.dumps(qualifiers)
    return fact


@pytest.fixture
def fact():
    return make_fact
