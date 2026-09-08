#!/usr/bin/env python
"""Write the four required cases and corpus statistics to `cases/` as committed artifacts.

The assignment asks for enough sample output to evaluate the system without
needing our credentials. These files are generated from the live database by the
same code paths the API uses, so they are a snapshot of real output rather than a
hand-written summary.

    python scripts/export_cases.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from factlayer.cases import build_cases          # noqa: E402
from factlayer.config import get_settings        # noqa: E402
from factlayer.db import Store                   # noqa: E402
from factlayer.normalize.units import humanize    # noqa: E402

OUT = ROOT / "cases"


def fact_block(fact: dict, label: str) -> str:
    lines = [f"**{label} — {fact['subject_raw']} · {fact['metric_raw']}**", ""]
    lines.append(f"- Value as printed: `{fact['value_raw']}`")
    if fact.get("value_num") is not None:
        lines.append(f"- Normalized: `{humanize(fact['value_num'], fact.get('value_unit') or '')}`")
    if fact.get("period_label"):
        resolved = fact.get("period_canonical") or "unresolved"
        lines.append(f"- Period: `{fact['period_label']}` → `{resolved}`")
    qualifiers = {k: v for k, v in (fact.get("qualifiers") or {}).items() if k != "period"}
    if qualifiers:
        lines.append("- Qualifiers: " + ", ".join(f"`{k}={v}`" for k, v in sorted(qualifiers.items())))
    lines.append(f"- Source: `{fact['doc_filename']}`, page {fact['page']}")
    lines.append("")
    lines.append("> " + (fact.get("evidence_text") or "").replace("\n", " ").strip())
    lines.append("")
    return "\n".join(lines)


def observation_block(detail: dict) -> str:
    obs = (detail or {}).get("observation") or {}
    if not obs:
        return ""
    rows = []
    add = lambda k, v: rows.append(f"| {k} | {v} |")
    add("period relation", f"`{obs.get('period_relation')}` — {obs.get('period_note', '')}")
    if obs.get("units_comparable"):
        add("units", f"`{obs.get('units_a')}` ↔ `{obs.get('units_b')}` (comparable)")
        add("values compared", f"`{obs.get('value_a'):,.6g}` vs `{obs.get('value_b'):,.6g}`")
        if obs.get("rel_diff") is not None:
            add("relative difference", f"`{obs['rel_diff'] * 100:.4f}%`")
        if obs.get("within_tolerance") is not None:
            add("verdict on that", "within rounding tolerance" if obs["within_tolerance"]
                else "**outside** rounding tolerance")
        add("rounding tolerance", f"`{obs.get('tolerance', 0) * 100:.4f}%` (from how precisely each figure is written)")
        if obs.get("ratio") is not None:
            add("ratio A/B", f"`{obs['ratio']:.6g}`")
    else:
        add("units", f"`{obs.get('units_a')}` vs `{obs.get('units_b')}` — **not directly comparable**")
    for key, pair in (obs.get("qualifier_deltas") or {}).items():
        add(f"qualifier `{key}`", f"A=`{pair[0] or '(unstated)'}` · B=`{pair[1] or '(unstated)'}`")
    for i, hypothesis in enumerate(obs.get("hypotheses") or [], 1):
        add(f"hypothesis {i}", hypothesis)
    if detail.get("rule_verdict"):
        verdict = detail["rule_verdict"]
        add("rule-based verdict", f"`{verdict}` — " + ("**overturned** by the adjudicator" if detail.get("overturned") else "confirmed by the adjudicator"))
    return "\n<details><summary>Mechanical observations the decision rests on</summary>\n\n| observation | value |\n|---|---|\n" + "\n".join(rows) + "\n\n</details>\n"


def relation_section(relation: dict, index: int) -> str:
    scope = "cross-document" if relation.get("cross_doc") else "same document"
    head = (f"### {index}. {relation['kind']}"
            f"  ·  confidence {relation.get('score', 0):.2f}"
            f"  ·  {scope}"
            f"  ·  decided by `{relation.get('method')}`")
    if relation.get("dimension"):
        head += f"  ·  explained by **{relation['dimension']}**"
    parts = [head, ""]
    parts.append(fact_block(relation["a"], "Fact A"))
    parts.append(fact_block(relation["b"], "Fact B"))
    parts.append(f"**System reasoning.** {relation.get('rationale', '')}")
    parts.append(observation_block(relation.get("detail") or {}))
    return "\n".join(parts)


def main() -> int:
    settings = get_settings()
    store = Store(settings.db_path)
    stats = store.stats()
    if not stats["facts"]:
        print("No facts in the database. Run `factlayer ingest ...` first.", file=sys.stderr)
        return 1

    cases = build_cases(store, per_case=3)
    OUT.mkdir(exist_ok=True)
    (OUT / "cases.json").write_text(json.dumps(cases, indent=2, default=str), encoding="utf-8")

    documents = store.query("SELECT * FROM documents ORDER BY ingested_at")
    lines = [
        "# The four required cases",
        "",
        "Generated from the live knowledge layer by `scripts/export_cases.py`. Nothing here is",
        "hand-written or hard-coded: each case is the top-ranked example of its kind among the",
        "relations the system actually produced, selected by `factlayer/cases.py`.",
        "",
        "## Corpus",
        "",
        "| document | pages | facts | primary entity |",
        "|---|---:|---:|---|",
    ]
    for document in documents:
        n = store.one("SELECT COUNT(*) AS n FROM facts WHERE doc_id = ?", (document["id"],))["n"]
        lines.append(f"| `{document['filename']}` | {document['n_pages']} | {n} | {document.get('primary_entity') or '—'} |")
    lines += [
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in stats.items():
        if key == "by_kind":
            for kind, count in sorted(value.items()):
                lines.append(f"| relations · {kind} | {count:,} |")
        else:
            lines.append(f"| {key.replace('_', ' ')} | {value:,} |" if isinstance(value, int) else f"| {key} | {value} |")

    headings = {
        "corroboration": ("Case 1 — A fact corroborated across documents, expressed differently",
                          "Ranked by how *differently* the two sources state the same agreeing fact, so the "
                          "examples shown are the ones that only match because of normalization."),
        "contradiction": ("Case 2 — A genuine or likely contradiction",
                          "Same metric, same subject, same resolved period, and no stated difference in basis, "
                          "scope or units — yet the figures disagree by more than rounding can explain."),
        "reconciled":    ("Case 3 — An apparent contradiction explained by context",
                          "The numbers disagree, but a stated difference in period, basis, scope, unit or "
                          "currency accounts for it. The dimension that resolves the conflict is named."),
    }
    for key, (title, blurb) in headings.items():
        lines += ["", "---", "", f"## {title}", "", blurb, ""]
        examples = cases[key]["examples"]
        if not examples:
            lines.append("_No example of this case is present in the current knowledge layer._")
            continue
        for i, relation in enumerate(examples, 1):
            lines.append(relation_section(relation, i))

    failure = cases["failure"]
    lines += ["", "---", "", "## Case 4 — Extraction and reasoning failures", "",
              "Measured, not estimated. Every proposed fact is checked against the real page text before",
              "storage; failures are written to a quarantine table with a reason instead of being dropped.", "",
              "| measure | value |", "|---|---:|"]
    for key, value in (failure.get("summary") or {}).items():
        lines.append(f"| {key.replace('_', ' ')} | {value} |")
    if failure.get("quarantine_reasons"):
        lines += ["", "### Why facts were rejected", "", "| reason | count |", "|---|---:|"]
        for reason in failure["quarantine_reasons"]:
            lines.append(f"| `{reason['reason']}` | {reason['n']} |")
    samples = failure.get("hallucinated_evidence_samples") or []
    if samples:
        lines += ["", "### Quotes the model produced that are not in the document", "",
                  "These were rejected before storage. They are the clearest evidence that grounding does real work.", ""]
        for sample in samples:
            payload = sample.get("payload") or {}
            lines += [f"- **{payload.get('metric', '—')} = {payload.get('value', '—')}** "
                      f"(claimed page {payload.get('page', '?')})",
                      f"  > {(payload.get('evidence') or '').replace(chr(10), ' ')[:300]}", ""]
    overturned = failure.get("overturned_examples") or []
    if overturned:
        lines += ["", "### Where the adjudicator overturned the deterministic verdict", "",
                  "The most useful place to look for reasoning errors on either side.", ""]
        for i, relation in enumerate(overturned[:2], 1):
            lines.append(relation_section(relation, i))

    (OUT / "CASES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'CASES.md'} and {OUT / 'cases.json'}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
