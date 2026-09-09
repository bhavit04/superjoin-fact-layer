# Fact Knowledge Layer

Extract checkable facts from PDFs, tie every one to the words that support it, and
work out whether facts from different documents **agree**, **genuinely conflict**, or
only *appear* to conflict because they were measured differently.

The distinction the whole system is built around:

> **Two values disagreeing is not the same as two sources contradicting each other.**

Financial and macroeconomic documents are full of figures that differ for perfectly
good reasons — a different fiscal period, consolidated versus standalone accounts,
crore versus million, a forecast against an actual, one publisher's vintage against
another's. A system that flags all of those as contradictions is useless, and so is
one that explains all of them away. The interesting work is telling them apart, and
being able to show *why* for each decision.

---

## Setup and run instructions

Requires **Python 3.11+**. No database server, no vector store, no Docker.

```bash
git clone <this-repo> && cd superjoin-fact-layer
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Run it with no API key at all

This repository ships the model's cached responses for the six starter documents, so
the whole knowledge layer can be rebuilt offline and the API browsed without a
credential:

The six starter PDFs are committed too, so this needs no setup beyond the install:

```bash
FACTLAYER_PROVIDER=replay factlayer ingest data_raw/starter-datasets/*/*.pdf
factlayer serve                      # http://127.0.0.1:8000
```

The cache is keyed by the text of each chunk, so those six documents hit it and the
rebuild runs without a network call. Any other PDF simply misses, and needs a key.

Pre-generated output is also committed, if you would rather just read it:

- **[`cases/CASES.md`](cases/CASES.md)** — the four required cases with full evidence and reasoning
- [`cases/cases.json`](cases/cases.json) — the same thing as raw API output

### Run it against your own PDFs

You need a key for one provider. Gemini has a free tier
([aistudio.google.com/apikey](https://aistudio.google.com/apikey)):

```bash
cp .env.example .env      # then put your key in it. .env is gitignored.
factlayer serve
```

Open <http://127.0.0.1:8000> and drop PDFs onto the page. Or use the CLI:

```bash
factlayer ingest path/to/*.pdf     # incremental: links against what is already stored
factlayer cases                    # print the four cases
factlayer stats                    # corpus statistics
pytest -q                          # 81 tests; 73 need no PDFs and no key
```

Set `FACTLAYER_PROVIDER` to `gemini`, `anthropic`, or `openai`. The code is the same
either way; only the transport differs.

```bash
factlayer doctor      # what your key can actually reach, before you rely on it
```

### What to expect on a free tier

Ingesting one PDF costs roughly one model call per five pages, plus a bounded number
of adjudications:

| document | model calls | wall time on a free key |
|---|---:|---|
| a 27-page deck | ~25 | under a minute |
| a 100-page report | ~50 | about three minutes |

Google's free tier allows 500 requests/day on `gemini-3.1-flash-lite`, so a reviewer
can process a dozen documents before running out. Two behaviours matter if you do hit
a limit: the client paces requests below the rate limit rather than bursting into it,
and treats repeated rejections as exhaustion — rotating to the next model in the
chain, then failing fast with a clear message rather than retrying into a wall.
Anything already cached still replays, so an interrupted run resumes.

Google also retires models per key vintage: a key issued today is refused some older
models outright. The client detects that and moves down the chain, and `factlayer
doctor` reports it directly.

### The API

| endpoint | what it does |
|---|---|
| `POST /api/documents` | upload one or more PDFs; returns a job id |
| `GET /api/jobs/{id}` | live ingestion progress |
| `GET /api/facts` | search facts by text, document, or type |
| `GET /api/facts/{id}` | one fact with everything related to it |
| `GET /api/facts/{id}/evidence.png` | **the source page, with the evidence highlighted** |
| `GET /api/relations` | browse links, filtered by kind / dimension / cross-document |
| `GET /api/claims` | **everything every source says about one quantity**, grouped and ranked |
| `GET /api/cases` | the four required cases, selected from live data |
| `GET /api/schema` | the fact schema as it has accumulated from documents |
| `GET /api/quarantine` | facts that were rejected, and why |

---

## What it produces on the starter corpus

<!--STATS-->
| document | pages | facts | grounded |
|---|---:|---:|---:|
| `03-delhivery-q4-fy24-earnings-presentation.pdf` | 27 | 118 | 79% |
| `02-delhivery-annual-report-fy24-excerpt.pdf` | 100 | 968 | 93% |
| `01-delhivery-prospectus-2022-excerpt.pdf` | 100 | 724 | 88% |
| `01-india-economic-survey-2024-25-excerpt.pdf` | 89 | 329 | 100% |
| `02-rbi-annual-report-2024-25-excerpt.pdf` | 100 | 622 | 94% |
| `03-imf-india-2025-article-iv-excerpt.pdf` | 95 | 371 | 83% |
| **6 documents** | **511** | **3,132** | **91%** |

| relationship | count | |
|---|---:|---|
| **CORROBORATES** | 203 | the same claim, agreeing |
| **RECONCILED** | 291 | disagreeing, but a stated difference in context explains it |
| **CONTRADICTS** | 10 | disagreeing with nothing to explain it |
| **RELATED** | 2,209 | same metric, different periods — a time series |
| _of which cross-document_ | 611 | |

The fact schema grew to **1,325 metric names** and **107 qualifier keys** across **671 subjects** — none of it declared in advance. **77** proposed facts were rejected for failing to ground.
<!--/STATS-->

Every number in those two tables is read out of the database by `make readme-stats`,
not typed. Full output, with evidence and reasoning for every example, is in
**[`cases/CASES.md`](cases/CASES.md)**. `make verify` re-checks all of this against the
database and exits non-zero if any of it stops being true.

---

## Video demo

**[Watch the demo (2:16)](https://github.com/bhavit04/superjoin-fact-layer/blob/main/build/fact-knowledge-layer-demo.mp4)** — plays
inline on GitHub; [direct download](https://github.com/bhavit04/superjoin-fact-layer/raw/main/build/fact-knowledge-layer-demo.mp4).

A screencast of the running system: a PDF being ingested, then all four required
cases with their real evidence and reasoning. Nothing in it is staged — every number
on screen comes from the API responses shown.

It is a real recording of the running app with the captions drawn on afterwards —
no slides, and no narration over a mockup.

---

## Approach

### The pipeline

```
PDF
 │
 ├─ 1. chunk           page-aware, bounded by both page count and characters
 │
 ├─ 2. extract         model proposes structured claims, with a verbatim quote
 │
 ├─ 3. GROUND          every quote is located in the real page text,
 │                     or the fact is quarantined with a reason
 │
 ├─ 4. normalize       units → one magnitude · periods → intervals
 │                     entities → canonical keys · metrics → a shared vocabulary
 │
 ├─ 5. candidates      IDF-weighted inverted index picks pairs worth comparing
 │
 ├─ 6. OBSERVE         mechanical facts about each pair: units reconciled,
 │                     period relationship, ratio, rounding tolerance,
 │                     which qualifiers differ
 │
 ├─ 7. classify        deterministic rules settle ~90% of pairs outright
 │
 └─ 8. adjudicate      only the rest reach a model — and it receives the
                       observations, so it judges rather than calculates
```

Steps 3, 6 and 7 are where the real engineering is. Steps 2 and 8 are the only ones
that call a model.

### What counts as a fact

The documents decide, not a schema. A fact is:

```jsonc
{
  "subject":  "Delhivery Limited",          // resolved from "the Company"
  "metric":   "revenue from services",      // canonicalized into a shared vocabulary
  "value":    "₹8,142 Cr",                  // verbatim, plus a normalized magnitude
  "qualifiers": {                           // ← an OPEN object: no fixed key set
    "period": "FY24",
    "basis":  "consolidated"
  },
  "evidence": "₹8,142 Cr\nFY24 revenue from services",
  "page": 6
}
```

`qualifiers` is the important part. Nothing enumerates its keys. A document that
introduces a dimension the system has never seen — `measure`, `counterparty`,
`vintage`, anything — stores it, registers it in the schema registry, and it
participates in comparison immediately. No migration, no code change.

### Grounding: the model proposes, the document disposes

Every fact carries a quote the model claims to have copied. That claim is checked
against the actual page text before the fact is stored — exact match first, then a
bounded fuzzy alignment for PDF extraction artefacts like hyphenation and column
reordering. A quote that cannot be found near the cited page is **rejected**, and
written to a quarantine table with a reason.

This is the guard that turns "the model said so" into "the document says so", and it
is measurable: see Case 4 in [`cases/CASES.md`](cases/CASES.md) for the fabricated
quotes it actually caught.

Facts that match only fuzzily are kept but have their confidence scaled down by the
match quality, and the UI marks them.

### Normalization is what makes comparison possible

Nothing can be compared until it is on a common footing:

- **Units.** `Rs. 8,142 Mn` = `₹814.2 crore` = `81,420 lakh`. Indian lakh/crore
  scales, `1,23,456` digit grouping, accounting negatives `(1,234)`, ranges
  (`6.3 to 6.8 per cent`), basis points, and unit hints carried down from table
  headers. Different currencies deliberately stay *incomparable* — that is a
  currency difference to explain, not a conflict.
- **Periods.** `FY24`, `FY 2023-24`, `2023-24` and `the year ended March 31, 2024`
  all resolve to `2023-04-01 → 2024-03-31`. `Q4 FY24` resolves to `2024-01-01 →
  2024-03-31` and is then *known to nest inside* FY24. Balance-sheet instants
  (`as at March 31, 2024`) are kept distinct from periods. A bare `2024` is flagged
  ambiguous rather than guessed at.
- **Entities.** Legal suffixes stripped, and anaphora resolved: annual reports say
  "the Company" far more often than they say their own name, so each document's
  primary entity is inferred from what the extractor actually saw and used to
  resolve those references.
- **Metrics.** Lexical similarity handles "revenue from operations" ≈ "operating
  revenue" but will never handle "CPI inflation" ≈ "consumer price inflation". That
  judgement goes to a model — **once per distinct metric label, not once per fact
  pair**, and only for labels not seen before. Six documents produce a few hundred
  labels and thousands of facts, so this costs one or two calls per document.

### Deciding how two facts relate

For each candidate pair the system first computes what can be established without
opinion: units reconciled onto one scale, the period relationship
(`EQUAL` / `CONTAINS` / `DISJOINT` / …), the ratio, which qualifiers differ, and a
**rounding tolerance derived from how precisely each figure was written**.

That last one matters more than it sounds. `Rs 814 crore` states the value only to
the nearest crore, so demanding it match `Rs. 8,142 Mn` to within 0.01% would
manufacture a contradiction out of rounding. Tolerance is half a unit in the last
stated decimal place.

Deterministic rules then settle most pairs:

| situation | verdict |
|---|---|
| same period, agree within stated precision | **CORROBORATES** |
| same period, differ, but a stated `basis`/`scope`/`unit` differs too | **RECONCILED**, dimension named |
| same period, differ, ratio ≈ 10 / 100 / 10⁷ | **RECONCILED** — scale mismatch |
| different currencies | **RECONCILED** — needs an exchange rate |
| one period nests inside the other | **RECONCILED** — reporting window |
| a part exceeding its whole (for additive metrics) | **CONTRADICTS** |
| non-overlapping periods | **RELATED** — a time series, not a conflict |
| a level versus its growth rate / margin / share | **RELATED** — different claims |
| **same period, same scope, no explanation, values differ** | **CONTRADICTS** |

**Before any of that runs, the pair has to earn a comparison.** Two facts are only
compared when a model has explicitly clustered their metric names, or the names are
token-for-token equivalent after stemming. Plain similarity is not enough, and this
is the single most consequential rule in the system. An earlier version compared
anything scoring above a threshold, and produced this:

```
net cash from / (used in) OPERATING activities   =  (30)     FY23
net cash from / (used in) INVESTING activities   =  (3,411)  FY23
net cash from / (used in) FINANCING activities   =   3,538   FY23
```

Five of six tokens shared, similarity 0.67 — and three unrelated line items, each
pair reported as a confident, fully-evidenced, completely false contradiction. One
document alone produced 33 of them. Under the equality rule it produces none, which
for a single source is the right answer.

The cost is real: synonyms whose words differ ("CPI inflation" / "consumer price
inflation") now depend entirely on the clustering pass, and some true links are
lost when it does not fire. That trade is deliberate. A missed link is invisible
and recoverable; an invented contradiction discredits every other claim the system
makes.

Only pairs the rules cannot settle go to a model, and they arrive with the
observations attached, so it is arbitrating a judgement rather than doing arithmetic
it is bad at. Every relation records which path produced it (`deterministic`,
`hybrid`, `llm`), and the UI and exported cases show the observation table behind
each decision.

### Claims: above the pairwise view

A relation answers *"do these two agree?"*. That is the right unit for the machine
and the wrong one for a reader, whose actual question is *"what does every source
say about this, and do they line up?"*

`/api/claims` groups facts sharing a subject, metric and period, reports the spread
across sources, and carries through whatever the pairwise pass found explained the
difference. It is pure aggregation over stored data — no model calls — and it
surfaces the single most interesting disagreement in the corpus without being asked:

```
India · current account deficit · FY2025          sources disagree, spread 50%
  1.20 %   Economic Survey 2024-25   p.62   "…1.2 per cent of GDP in Q2 FY25"
  0.60 %   IMF Article IV 2025       p.52   "The CA deficit declined to 0.6 percent…"
```

Two institutions, one quantity, one screen. This is the layer a claim-level truth
model would be built on, and it is listed under next steps for that reason.

### Scaling, and the brownie points

- **Large PDFs.** Text extraction and grounding are per-page and cached; chunks are
  bounded by *both* page count and characters, because these corpora mix 10k-character
  financial-note pages with 300-character slides.
- **Many PDFs in one layer.** Comparing every fact to every other is O(n²) — about 18
  million pairs at 6,000 facts. An IDF-weighted inverted index over metric tokens,
  plus an entity check, reduces this to a bounded top-K per fact, so pair generation
  is roughly linear.
- **Incremental ingestion.** Documents are content-addressed, so re-uploading is a
  no-op. A new document is probed against the index of everything already stored;
  **existing facts and relations are never recomputed**. Ingesting the seventh
  document costs roughly what the second did.
- **A schema that evolves.** The `schema_registry` table accumulates every metric,
  qualifier key, unit and entity as documents introduce them. `GET /api/schema` shows
  the current shape of the knowledge layer — a schema grown from documents rather than
  declared in advance.

### Is this RAG?

No, and the difference is worth stating. RAG retrieves passages *at query time* and
feeds them to a model to generate an answer. Here, nothing is generated at query
time: the API serves structured rows and pre-computed relationships. The model is
used for **extraction** (turn a chunk into structured claims) and **adjudication**
(judge how two *already-structured* facts relate), never to answer from retrieved
text. There is a retrieval step, but it retrieves *candidate fact pairs for
comparison* — blocking for record linkage, not context for a prompt.

The sharpest difference: RAG has no concept of two sources disagreeing. This system
exists to find that. The nearest accurate labels are knowledge-base construction and
claim reconciliation.

### Engineering decisions and trade-offs

**SQLite, not a graph database.** The brief warns that a graph database is not the
solution, and it is right: the queries this system runs are "facts sharing a metric
cluster and entity" and "relations touching this fact", both ordinary indexed
lookups. A single file also makes the project clone-and-run. The cost is that
multi-hop traversal would need real work to add.

**Deterministic first, model second.** Roughly nine in ten pairs never reach a model.
That is cheaper and faster, but the real reason is explainability: a rationale that
cites reconciled units and an interval comparison can be checked by a reader, while
"the model thought so" cannot.

**Lexical prefilter, semantic clustering.** Embeddings for every fact would have
meant a heavyweight dependency and would still over-match levels against growth
rates. Clustering *distinct metric labels* with a model instead puts the semantic
judgement where it is cheap and auditable.

**A prompt-keyed response cache.** The cache key is a hash of the prompt, not of the
provider, so a cache built with one model replays under any configuration — which is
what lets this repo ship a runnable demo with no credential, and makes a long
throttled ingest resumable.

**Conservative metric merging.** Wrongly merging two metrics *invents* contradictions
that are not in the documents. The clustering prompt and the lexical fallback
threshold both bias hard toward leaving names separate.

**Pacing rather than retrying.** Free-tier quotas are metered per model and per day,
and a rejected request still consumes budget — so retrying into a limit makes things
strictly worse. Requests are paced by a token bucket below the limit; three
consecutive 429s on a model are treated as exhaustion and the client rotates to the
next model in the chain; when all are spent a breaker fails fast instead of making
every remaining call pay for six pointless retries. Because responses are cached by
prompt, an interrupted run resumes rather than restarts.

### AI tools used

Built with **Claude Code** (Opus 5) — architecture, implementation, and the test
suite were developed interactively with it. Two bugs it wrote were caught by tests it
also wrote: a float-keyed lookup table that silently dropped entries because
`10_000_000/1_000_000 == 10` collided with an existing key, and a currency mismatch
that fell through to the text-comparison branch and read as a contradiction.

The runtime system uses **Gemini** (`gemini-3.1-flash-lite`) by default, behind a
provider-agnostic interface that also speaks Anthropic and OpenAI. That model was
not the first choice — it was picked after measuring: on the same chunk it extracted
more facts than the larger `gemini-3.6-flash` (46 against 37) in a third of the time.

---

## Limitations and next steps

Written honestly; several of these are visible in the "Failures" tab of the UI.

**What does not work well yet**

- **No OCR.** Text comes from the PDF's text layer, so a scanned document yields
  nothing. Ingest detects this and says so rather than reporting an empty document,
  because the two look identical from the outside. OCR was left out deliberately
  rather than overlooked: every fact here is verified by finding its quote verbatim
  in the page, and OCR's character-level errors would break those matches and
  quarantine facts that are actually correct. Running a scan through OCR first, then
  ingesting the result, is the right order of operations.
- **English only.** The prompts, stopword lists and period vocabulary are English.

- **Tables are partly solved; the rest is the largest remaining gap.** Linear text
  extraction returns a PDF's runs in storage order, which for a column-major table
  interleaves labels and values so a row cannot be read back. The geometry survives
  that, and is now used: words are clustered by vertical position to rebuild the row a
  reader sees, and a quote whose tokens all sit on one such row is grounded. That took
  quarantined facts from 180 to 77 and grounded 51 facts that were previously
  rejected. PyMuPDF's own `find_tables` was measured on the same failures first and
  recovered 0 of 35 — these tables have no ruling lines. What remains unsolved is
  column association: rows are rebuilt, columns are not, so a figure still cannot be
  tied to the header above it, and on a two-column page a rebuilt row spans both
  columns. Proper column clustering is the highest-value thing left to build.
- **Periods that need document context.** "the prior year" or "the previous quarter"
  resolve to nothing, because resolving them requires knowing the document's own
  reporting date. Those facts are stored with an unresolved period and are then only
  comparable when the other side is unresolved too.
- **A bare year is genuinely ambiguous.** IMF documents often mean the Indian fiscal
  year by "2024" while using calendar years elsewhere. This is flagged, not solved.
- **Cross-currency pairs are never resolved.** An INR figure and a USD figure for the
  same metric are correctly reported as a currency difference, but the system does
  not fetch a period-appropriate exchange rate to check whether they actually agree.
- **The adjudication budget is a blunt instrument.** Pairs beyond the per-document
  budget keep their rule-based verdict. They are ranked so conflicts are spent first,
  but a long tail goes unadjudicated and is labelled as such.
- **No confidence calibration.** Confidence is a heuristic blend of the model's
  self-reported number and the grounding match quality. It orders results usefully
  but should not be read as a probability.
- **Single-hop only.** If A corroborates B and B contradicts C, nothing notices that A
  and C are in tension.
- **No ground truth, so precision is argued rather than measured.** Contradictions fell
  from 138 to 9 as false-positive classes were found and fixed, and each fix is named
  and regression-tested — but that evidence is examples I inspected, not a labelled
  set. Nothing here proves real contradictions were not suppressed along the way. The
  right next step is to hand-label a few hundred pairs and report precision and recall
  properly.
- **The thresholds were chosen on this corpus, but they are not load-bearing.** No
  fact, filename or metric is hard-coded — logic never branches on document content —
  but the judgement cutoffs were picked by inspecting these six documents. Rather than
  argue they generalise, `scripts/sensitivity.py` measures it: each is swept across a
  plausible range and every relation re-derived. **No threshold moves more than 3.6% of
  verdicts**, and most move under 1%.

  ```
  shared_evidence   0.80 → 0.99     verdicts move 0.0% – 3.5%
  enumeration_min   2 → 6           verdicts move 0.0% – 3.6%
  text_equality     0.70 → 0.94     verdicts move 0.0% – 0.3%
  attribution_floor 0.10 → 0.70     verdicts move 0.0% – 0.1%
  scale_window      0.05 → 0.30     verdicts move 0.0% – 0.1%
  ```

  The sweep also found a threshold that did nothing: a metric-similarity cutoff that
  could never bind, because token-set equality already gates every comparison. It has
  been removed. The parts that carry the weight are derived rather than tuned — the
  rounding tolerance comes from how precisely each figure is written, the period
  algebra is calendar arithmetic, and the fiscal-year convention is read off each
  document.
- **Recall depends on the clustering pass.** Because comparison requires metric-name
  equality or an explicit cluster, a metric the clustering pass fails to merge simply
  never gets compared. That failure is silent — there is no signal distinguishing
  "these documents agree on nothing" from "the vocabulary never joined them up".
- **Segments sometimes land in the subject.** The extractor occasionally records a
  business segment ("Express Parcel") as the fact's subject rather than as
  `qualifiers.scope`. Those facts then cannot link to another document that attributes
  the same quantity to the parent company. The fix is a prompt change, deliberately
  not made late in the build because it would invalidate the response cache the
  offline demo depends on.

**What I would build next, in order**

1. **Table-aware extraction** — detect table regions and extract cells with their row
   and column headers intact. Biggest quality win available.
2. **A claim-level truth model** — instead of pairwise verdicts, group all facts about
   one (entity, metric, period) into a claim and reason over the whole set, weighting
   sources by recency and authority. That is how "an audited annual report beats an
   earnings deck" would become a rule the system can apply.
3. **Transitive consistency checks** — propagate verdicts across the relation graph to
   surface the A-versus-C tension above.
4. **Period-aware currency reconciliation** — resolve cross-currency pairs against a
   rate for the period in question.
5. **A question-answering layer on top** — answer from *verified, reconciled* facts
   rather than raw chunks, so answers inherit the contradiction awareness. This is
   where RAG would genuinely belong, and it would be built on the knowledge base
   rather than instead of it.

---

## Additional notes

- **No credentials in the repository.** `.env` is gitignored; `.env.example` shows
  the shape. The committed response cache contains model *outputs* only.
- **The tests are the specification.** `tests/test_reconcile.py` encodes the four
  required cases as assertions over synthetic facts, so the
  corroborate/contradict/reconcile distinction is verifiable in under a second with
  no API key and no PDFs.
- **Nothing is hard-coded to these documents.** No filename, metric name, company or
  figure appears in the logic. The extraction prompt's worked example uses an invented
  company specifically so the model learns the *shape* of a fact rather than which
  facts to look for. The four cases in `cases/CASES.md` are chosen by ranking live
  relations, so a different corpus produces different examples through the same code.
- **Git history is decomposed by concern** rather than squashed, if you want to read
  the build in order.
