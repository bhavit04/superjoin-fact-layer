/* Fact Knowledge Layer - UI. Vanilla JS, no build step. */

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const api = async (path, options) => {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
};

const state = { tab: "cases", pollTimer: null };

// Must match the zoom used when rendering evidence pages server-side.
const EVIDENCE_ZOOM = 2.0;

/* ---------- rendering helpers ---------- */

function factSide(fact, label) {
  if (!fact) return `<div class="side"><div class="side-label">${label}</div><p class="muted">missing</p></div>`;
  const chips = [];
  if (fact.period_label) {
    const resolved = fact.period_canonical && fact.period_canonical !== fact.period_label
      ? ` → ${esc(fact.period_canonical)}` : "";
    chips.push(`<span class="chip period">${esc(fact.period_label)}${resolved}</span>`);
  }
  for (const [key, value] of Object.entries(fact.qualifiers || {})) {
    if (key === "period") continue;
    chips.push(`<span class="chip"><b>${esc(key)}</b> ${esc(value)}</span>`);
  }
  const normalized = fact.value_num != null
    ? `<small>normalized: ${Number(fact.value_num).toLocaleString(undefined, { maximumFractionDigits: 4 })} ${esc(fact.value_unit || "")}</small>` : "";
  const fuzzy = fact.match_ratio != null && fact.match_ratio < 0.995
    ? ` <span class="muted">(fuzzy match ${(fact.match_ratio * 100).toFixed(0)}%)</span>` : "";
  return `
    <div class="side">
      <div class="side-label">${label}</div>
      <div class="subject">${esc(fact.subject_raw)}</div>
      <div class="metric">${esc(fact.metric_raw)}</div>
      <div class="value">${esc(fact.value_raw)}${normalized}</div>
      <div class="chips">${chips.join("")}</div>
      <blockquote>${esc(fact.evidence_text)}</blockquote>
      <div class="src">
        <span>${esc(fact.doc_filename)} · p.${fact.page}${fuzzy}</span>
        <button data-evidence="${fact.id}">view in source</button>
      </div>
    </div>`;
}

function observationList(detail) {
  const obs = detail?.observation;
  if (!obs) return "";
  const rows = [];
  const add = (k, v) => { if (v !== undefined && v !== null && v !== "" ) rows.push([k, v]); };
  add("metric similarity", obs.metric_similarity);
  add("period relation", `${obs.period_relation} — ${obs.period_note || ""}`);
  if (obs.units_comparable) {
    add("units reconciled", `${obs.units_a} ↔ ${obs.units_b}`);
    add("values compared", `${Number(obs.value_a).toLocaleString()} vs ${Number(obs.value_b).toLocaleString()} ${obs.units_a}`);
    if (obs.rel_diff != null) add("relative difference", `${(obs.rel_diff * 100).toFixed(4)}%`);
    add("rounding tolerance", `${(obs.tolerance * 100).toFixed(4)}%`);
    if (obs.ratio != null) add("ratio A/B", Number(obs.ratio).toPrecision(6));
  } else {
    add("units", `${obs.units_a || "?"} vs ${obs.units_b || "?"} — not directly comparable`);
  }
  if (obs.range_contains != null) add("range containment", obs.range_contains ? "yes" : "no");
  for (const [key, pair] of Object.entries(obs.qualifier_deltas || {})) {
    add(`qualifier "${key}"`, `${pair[0] || "(unstated)"} vs ${pair[1] || "(unstated)"}`);
  }
  (obs.hypotheses || []).forEach((h, i) => add(`hypothesis ${i + 1}`, h));
  if (detail.rule_verdict) add("rule verdict", `${detail.rule_verdict}${detail.overturned ? " (overturned by model)" : " (confirmed)"}`);
  if (!rows.length) return "";
  return `<details><summary>Mechanical observations the decision was based on</summary>
    <dl class="obs">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl></details>`;
}

function relationCard(rel) {
  const scope = rel.cross_doc ? "cross-document" : "same document";
  const dim = rel.dimension ? `<span class="meta">explained by: ${esc(rel.dimension)}</span>` : "";
  return `
    <article class="card">
      <div class="card-head">
        <span class="tag ${esc(rel.kind)}">${esc(rel.kind)}</span>
        <span class="meta">confidence ${Number(rel.score ?? 0).toFixed(2)}</span>
        <span class="meta">${esc(scope)}</span>
        <span class="meta">${esc(rel.method)}</span>
        ${dim}
      </div>
      <div class="pair">${factSide(rel.a, "Fact A")}${factSide(rel.b, "Fact B")}</div>
      <div class="why">
        <div class="why-label">Reasoning</div>
        ${esc(rel.rationale)}
        ${observationList(rel.detail)}
      </div>
    </article>`;
}

/* ---------- tabs ---------- */

const loaders = {
  async cases() {
    const target = $("#panel-cases");
    target.innerHTML = `<p class="lede">The four cases the assignment asks for, selected from whatever is currently
      in the knowledge layer by ranking live relations — nothing here is hard-coded to a document or a figure.</p>
      <p class="muted">Loading…</p>`;
    const data = await api("/api/cases");
    const sections = [
      ["corroboration", "Ranked by how <em>differently</em> the two sources express the same agreeing fact."],
      ["contradiction", "Same metric, same period, no stated difference in basis or scope — yet the figures disagree."],
      ["reconciled", "Looked like a conflict until a stated difference in context accounted for it."],
    ];
    let html = `<p class="lede">The four cases the assignment asks for, selected from whatever is currently
      in the knowledge layer by ranking live relations — nothing here is hard-coded to a document or a figure.</p>`;
    for (const [key, blurb] of sections) {
      const block = data[key] || {};
      const examples = block.examples || [];
      html += `<section style="margin-bottom:34px">
        <h2>${esc(block.title || key)}</h2>
        <p class="lede">${blurb}</p>
        ${examples.length ? examples.map(relationCard).join("")
          : `<div class="empty">No example of this case in the current knowledge layer.<br>
             <span class="muted">Ingest more documents, or this corpus genuinely contains none.</span></div>`}
      </section>`;
    }
    html += renderFailures(data.failure || {});
    target.innerHTML = html;
  },

  async facts() {
    const params = new URLSearchParams({
      q: $("#fact-q").value, doc: $("#fact-doc").value,
      fact_type: $("#fact-type").value, limit: "80",
    });
    const data = await api(`/api/facts?${params}`);
    $("#fact-count").textContent = `${data.total.toLocaleString()} facts`;
    $("#fact-list").innerHTML = data.facts.length ? `
      <div class="scroll"><table>
        <thead><tr><th>Subject</th><th>Metric</th><th>Value</th><th>Period</th><th>Source</th><th>Conf.</th></tr></thead>
        <tbody>${data.facts.map((f) => `
          <tr class="fact-row" data-fact="${f.id}">
            <td>${esc(f.subject_raw)}</td>
            <td>${esc(f.metric_raw)}<br><span class="muted" style="font-size:11.5px">${esc(f.metric_cluster || "")}</span></td>
            <td class="num">${esc(f.value_raw)}</td>
            <td>${esc(f.period_canonical || f.period_label || "—")}</td>
            <td class="muted" style="font-size:12px">${esc(f.doc_filename)}<br>p.${f.page}</td>
            <td class="num">${Number(f.confidence ?? 0).toFixed(2)}</td>
          </tr>`).join("")}</tbody>
      </table></div>` : `<div class="empty">No facts match.</div>`;
  },

  async relations() {
    const params = new URLSearchParams({
      kind: $("#rel-kind").value, cross_doc: $("#rel-cross").value,
      q: $("#rel-q").value, limit: "40",
    });
    const data = await api(`/api/relations?${params}`);
    $("#rel-count").textContent = `${data.total.toLocaleString()} relations`;
    $("#rel-list").innerHTML = data.relations.length
      ? data.relations.map(relationCard).join("")
      : `<div class="empty">No relations match.</div>`;
  },

  async schema() {
    const data = await api("/api/schema");
    const order = ["metric", "qualifier", "unit", "entity", "fact_type"];
    const blurb = {
      metric: "Metric names observed in documents, each folded into a canonical name so differently-worded facts can be compared.",
      qualifier: "Qualifier keys. Nothing declares these — a document that introduces a new dimension registers it here and it flows through comparison unchanged.",
      unit: "Units parsed from values.",
      entity: "Subjects facts are about, after suffix stripping and anaphora resolution.",
      fact_type: "Fact types in use.",
    };
    $("#panel-schema").innerHTML = `
      <h2>Schema, as accumulated</h2>
      <p class="lede">This is not a schema the system was given; it is the schema documents have produced so far.
      Ingesting a document about a new domain adds rows here rather than requiring a migration.</p>
      <div class="grid2">${order.filter((k) => data[k]?.length).map((kind) => `
        <section class="card" style="margin:0">
          <div class="card-head"><h3 style="margin:0">${esc(kind)}</h3>
            <span class="meta">${data[kind].length} distinct</span></div>
          <div style="padding:11px 15px"><p class="muted" style="font-size:12.5px;margin:0 0 10px">${blurb[kind] || ""}</p></div>
          <div class="scroll" style="border:0;border-radius:0;max-height:330px;overflow-y:auto">
            <table><thead><tr><th>key</th><th>canonical</th><th>n</th></tr></thead>
            <tbody>${data[kind].slice(0, 120).map((r) => `
              <tr><td>${esc(r.key)}</td><td class="muted">${esc(r.canonical !== r.key ? r.canonical : "")}</td>
              <td class="num">${r.count}</td></tr>`).join("")}</tbody></table>
          </div>
        </section>`).join("")}</div>`;
  },

  async documents() {
    const data = await api("/api/stats");
    $("#doc-list").innerHTML = data.documents.length ? `
      <div class="scroll"><table>
        <thead><tr><th>Document</th><th>Pages</th><th>Facts</th><th>Status</th><th>Time</th><th></th></tr></thead>
        <tbody>${data.documents.map((d) => `
          <tr>
            <td><b>${esc(d.filename)}</b><br><span class="muted" style="font-size:12px">${esc((d.title || "").slice(0, 90))}</span>
                ${d.primary_entity ? `<br><span class="muted" style="font-size:12px">primary entity: ${esc(d.primary_entity)}</span>` : ""}</td>
            <td class="num">${d.n_pages ?? "—"}</td>
            <td class="num" id="dc-${d.id}">…</td>
            <td>${esc(d.status)}${d.error ? `<br><span class="muted">${esc(d.error.slice(0, 80))}</span>` : ""}</td>
            <td class="num">${d.duration_s ? d.duration_s + "s" : "—"}</td>
            <td><button class="btn" data-delete="${d.id}">delete</button></td>
          </tr>`).join("")}</tbody></table></div>` : `<div class="empty">No documents yet. Upload a PDF above.</div>`;
    for (const d of data.documents) {
      api(`/api/facts?doc=${d.id}&limit=1`).then((r) => {
        const cell = $(`#dc-${d.id}`); if (cell) cell.textContent = r.total.toLocaleString();
      }).catch(() => {});
    }
  },

  async failures() {
    const data = await api("/api/cases");
    $("#panel-failures").innerHTML = renderFailures(data.failure || {}, true);
  },
};

function renderFailures(failure, standalone = false) {
  const s = failure.summary || {};
  const reasons = failure.quarantine_reasons || [];
  const samples = failure.hallucinated_evidence_samples || [];
  const fuzzy = failure.fuzzy_grounding_samples || [];
  const overturned = failure.overturned_examples || [];
  return `
    <section>
      <h2>${esc(failure.title || "Extraction and reasoning failures")}</h2>
      <p class="lede">Every proposed fact is checked against the real page text before it is stored. Facts whose quote
      cannot be found are quarantined with a reason rather than dropped silently, so extraction failure is measurable
      instead of invisible.</p>
      <div class="controls">
        ${Object.entries(s).map(([k, v]) => `<span class="pill"><b>${esc(String(v))}</b> ${esc(k.replace(/_/g, " "))}</span>`).join("")}
      </div>
      ${reasons.length ? `<div class="scroll" style="margin-bottom:20px"><table>
        <thead><tr><th>Rejection reason</th><th>Count</th></tr></thead>
        <tbody>${reasons.map((r) => `<tr><td>${esc(r.reason)}</td><td class="num">${r.n}</td></tr>`).join("")}</tbody>
      </table></div>` : `<div class="empty" style="margin-bottom:20px">Nothing was quarantined.</div>`}

      ${samples.length ? `<h3>Quotes the model produced that are not in the document</h3>
        <p class="muted" style="font-size:13px">These were rejected. They are the clearest evidence that grounding is doing real work.</p>
        ${samples.map((q) => `<article class="card"><div class="side">
            <div class="metric">${esc(q.payload?.metric || "—")} = ${esc(q.payload?.value || "—")}</div>
            <blockquote>${esc(q.payload?.evidence || "")}</blockquote>
            <div class="src">claimed page ${esc(String(q.payload?.page ?? "?"))} · rejected: ${esc(q.reason)}</div>
        </div></article>`).join("")}` : ""}

      ${fuzzy.length ? `<h3>Facts grounded only by fuzzy match</h3>
        <p class="muted" style="font-size:13px">Kept, but with confidence scaled down by how well the quote matched.</p>
        <div class="scroll" style="margin-bottom:20px"><table>
          <thead><tr><th>Metric</th><th>Value</th><th>Match</th><th>Page</th></tr></thead>
          <tbody>${fuzzy.map((f) => `<tr><td>${esc(f.metric_raw)}</td><td class="num">${esc(f.value_raw)}</td>
            <td class="num">${(f.match_ratio * 100).toFixed(0)}%</td><td class="num">${f.page}</td></tr>`).join("")}</tbody>
        </table></div>` : ""}

      ${overturned.length ? `<h3>Where the model overturned the rule-based verdict</h3>
        <p class="muted" style="font-size:13px">Disagreements between the deterministic pass and the adjudicator — the
        most useful place to look for reasoning errors on either side.</p>
        ${overturned.map(relationCard).join("")}` : ""}
    </section>`;
}

/* ---------- upload ---------- */

async function uploadFiles(files) {
  const pdfs = [...files].filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  if (!pdfs.length) return;
  const form = new FormData();
  pdfs.forEach((f) => form.append("files", f));
  $("#upload-log").innerHTML = `<div><span class="t">0.0s</span><span class="stage">upload</span><span>sending ${pdfs.length} file(s)…</span></div>`;
  const { job_id } = await api("/api/documents", { method: "POST", body: form });
  pollJob(job_id);
}

function pollJob(jobId) {
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    let job;
    try { job = await api(`/api/jobs/${jobId}`); } catch { return; }
    $("#upload-log").innerHTML = job.events.map((e) =>
      `<div><span class="t">${e.t}s</span><span class="stage">${esc(e.stage)}</span><span>${esc(e.message)}</span></div>`
    ).join("");
    $("#upload-log").scrollTop = 1e9;
    if (job.state === "done" || job.state === "error") {
      clearInterval(state.pollTimer);
      if (job.error) $("#upload-log").innerHTML += `<div><span class="t"></span><span class="stage">error</span><span>${esc(job.error)}</span></div>`;
      refreshStats(); loaders.documents();
    }
  }, 700);
}

/* ---------- evidence modal ---------- */

async function showEvidence(factId) {
  const { fact, relations } = await api(`/api/facts/${factId}`);
  $("#modal-title").textContent = `${fact.metric_raw} = ${fact.value_raw} — ${fact.doc_filename}, page ${fact.page}`;
  const mode = fact.grounding_mode && fact.grounding_mode !== "verbatim"
    ? ` · matched as <b>${esc(fact.grounding_mode)}</b>` : "";
  $("#modal-body").innerHTML = `
    <blockquote>${esc(fact.evidence_text)}</blockquote>
    <p class="muted" style="font-size:12.5px">Highlighted below on the actual page. Grounding match:
      ${(Number(fact.match_ratio ?? 0) * 100).toFixed(0)}%${fact.grounded ? "" : " (below the verification threshold)"}${mode}.</p>
    ${(fact.bbox || []).length ? `
      <img id="evidence-img" src="/api/facts/${factId}/evidence.png?crop=1"
           alt="the highlighted evidence on its source page">
      <details style="margin-top:12px"><summary>show the whole page</summary>
        <img style="margin-top:10px" src="/api/facts/${factId}/evidence.png"
             alt="full source page with evidence highlighted"></details>`
    : `<img src="/api/facts/${factId}/evidence.png" alt="source page">`}
    ${relations.length ? `<h3 style="margin-top:20px">${relations.length} related fact(s)</h3>
      ${relations.slice(0, 6).map((r) => relationCard({ ...r, a: fact, b: r.other })).join("")}` : ""}`;
  $("#modal").hidden = false;

}

/* ---------- shell ---------- */

async function refreshStats() {
  const data = await api("/api/stats");
  const s = data.stats;
  const kinds = s.by_kind || {};
  $("#pills").innerHTML = [
    `<span class="pill"><b>${s.documents}</b> docs</span>`,
    `<span class="pill"><b>${s.facts.toLocaleString()}</b> facts</span>`,
    `<span class="pill"><b>${s.relations.toLocaleString()}</b> links</span>`,
    `<span class="pill"><b>${kinds.CONTRADICTS || 0}</b> contradictions</span>`,
    `<span class="pill"><b>${kinds.RECONCILED || 0}</b> reconciled</span>`,
    `<span class="pill ${data.llm.live ? "live" : ""}">${esc(data.llm.provider)}:${esc(data.llm.model)} ${data.llm.live ? "live" : "cache-only"}</span>`,
  ].join("");
  const select = $("#fact-doc");
  if (select && select.options.length !== data.documents.length + 1) {
    select.innerHTML = `<option value="">all documents</option>` +
      data.documents.map((d) => `<option value="${d.id}">${esc(d.filename)}</option>`).join("");
  }
}

function switchTab(tab) {
  state.tab = tab;
  $$("nav button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === tab)));
  $$(".panel").forEach((p) => { p.hidden = p.id !== `panel-${tab}`; });
  loaders[tab]?.().catch((err) => {
    const panel = $(`#panel-${tab}`);
    if (panel) panel.innerHTML = `<div class="empty">Failed to load: ${esc(err.message)}</div>`;
  });
}

document.addEventListener("click", (event) => {
  const tabBtn = event.target.closest("nav button");
  if (tabBtn) return switchTab(tabBtn.dataset.tab);

  const evidenceBtn = event.target.closest("[data-evidence]");
  if (evidenceBtn) { event.stopPropagation(); return showEvidence(evidenceBtn.dataset.evidence); }

  const row = event.target.closest("[data-fact]");
  if (row) return showEvidence(row.dataset.fact);

  const del = event.target.closest("[data-delete]");
  if (del) {
    return api(`/api/documents/${del.dataset.delete}`, { method: "DELETE" })
      .then(() => { refreshStats(); loaders.documents(); });
  }

  if (event.target.id === "modal" || event.target.id === "modal-close") $("#modal").hidden = true;
});

document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#modal").hidden = true; });

window.addEventListener("DOMContentLoaded", () => {
  const drop = $("#drop");
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => {
    e.preventDefault(); drop.classList.add("over");
  }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => {
    e.preventDefault(); drop.classList.remove("over");
  }));
  drop.addEventListener("drop", (e) => uploadFiles(e.dataTransfer.files));
  $("#file-input").addEventListener("change", (e) => uploadFiles(e.target.files));
  $("#pick").addEventListener("click", () => $("#file-input").click());

  let debounce;
  const rerun = (fn) => { clearTimeout(debounce); debounce = setTimeout(fn, 220); };
  ["#fact-q", "#fact-doc", "#fact-type"].forEach((sel) =>
    $(sel).addEventListener("input", () => rerun(() => loaders.facts())));
  ["#rel-kind", "#rel-cross", "#rel-q"].forEach((sel) =>
    $(sel).addEventListener("input", () => rerun(() => loaders.relations())));

  refreshStats();
  switchTab("cases");
});
