# Demo video script (target: 2:40, hard limit 3:00)

Record at 1920×1080. Have `make serve` already running and the browser at
<http://127.0.0.1:8000>, plus a second PDF ready on the desktop to drag in.

---

### 0:00 – 0:20 · What the problem is

> "Documents state the same fact in different words, and different facts that look
> the same. This system extracts facts from PDFs, ties each one to the exact words
> that support it, and then works out whether two facts agree, genuinely conflict,
> or only look like they conflict."

Show the header stat pills: documents, facts, links, contradictions, reconciled.

### 0:20 – 0:50 · Ingesting a PDF  *(required: show a PDF being processed)*

Go to **Documents & upload**, drag a PDF in. Let the live log run.

> "Ingestion is incremental. Chunks are extracted in parallel, every quote is
> checked against the real page before it's stored, and the new facts are linked
> against everything already in the layer — nothing existing is recomputed."

Point at the log lines as they appear: `extracted`, `grounded`, `clustered`,
`candidates`, `adjudicate`, `linked`.

### 0:50 – 1:20 · Case 1 — corroboration  *(required)*

**Four cases** tab, first section. The strongest example on the starter corpus is
Delhivery shipment volume: the FY24 annual report states it inside a **chart series**
("225 289 582 663 740 / FY20 FY21 FY22 FY23 FY24") while the 2022 prospectus states it
in **prose** ("289.20 million orders in Fiscal 2021").

> "Two documents published two years apart. One states the figure in a chart, the
> other in a sentence. They call the metric different things and spell the period
> differently — 'FY21' against 'Fiscal 2021'. They match because units resolve to one
> magnitude and both period spellings resolve to the same interval."

Read the reasoning line aloud — it is the distinctive part:

> "…agree to within 0.07%, inside the 0.17% tolerance implied by how precisely each
> figure is written."

Expand **Mechanical observations** — point to `period relation: EQUAL`, the
reconciled units, and the relative difference sitting inside the rounding tolerance.

Click **view in source** on one side. Show the highlight on the real page.

> "Every fact links back to the page it came from."

### 1:20 – 1:55 · Case 2 — a genuine contradiction  *(required)*

> "Same metric, same subject, same resolved period, nothing stated that would
> explain a difference — and the numbers disagree by more than rounding allows.
> That's a real conflict, and the system says so rather than smoothing it over."

Show both evidence quotes side by side, then the reasoning line.

### 1:55 – 2:25 · Case 3 — explained by context  *(required)*

The best example is the **current account deficit**: the IMF reports 0.6% of GDP, the
Economic Survey reports 1.2%. Both periods resolve to FY2025, so this looks like two
institutions flatly disagreeing.

> "Two different institutions, the same metric, and both periods resolve to the same
> fiscal year — so the rules escalated it. The adjudicator then found the answer in
> the evidence itself: the IMF figure is the full year, the Survey figure is Q2 of
> that year. Reconciled on period, not a contradiction."

Point at the quoted supporting words in the reasoning. If time is tight, the food
inflation pair makes the same point in one line: RBI 6.7% for the full year against
the Survey's 8.4% for "FY25 (April–December)".

### 2:25 – 2:45 · Case 4 — failures  *(required)*

If you want the sharpest single line here, use the system diagnosing its **own**
extraction error: the adjudicator's reasoning on the working-capital-days pair reads
"Both facts are extracted from the same sequence of numbers ('73 47 37')… since '40'
does not appear in that sequence" — it caught a table misread that invented a value.

**Failures** tab.

> "Every quote the model proposes is checked against the page. These are quotes it
> produced that aren't in the document — they were rejected before storage. The
> quarantine table means extraction failure is measurable instead of invisible."

Point at the counts, then one rejected quote.

### 2:45 – 3:00 · Close

**Schema** tab, briefly.

> "Nothing here was declared up front — the schema is accumulated from documents,
> so a new kind of fact adds rows instead of needing a migration. And the whole demo
> replays from a committed cache, so you can run it with no API key."

---

**Don't** narrate the architecture; the README does that. Spend the time on the four
cases and on clicking through to real evidence.
