# Primer: The dashboard UI — what each part is & what runs behind it   ·   ~7 min   ·   [Comm · Exec]
> The frontend is a **thin client**. Every panel is just a view over the backend; the analytics live in
> DuckDB, not the browser. This maps each UI element → the exact endpoint / query object that feeds it.

## The mental model
Three surfaces, **one engine**. Presets, the query panel, and the charts all emit the **same query object**
and hit **one `POST /aggregate`**. The React app holds almost no logic — it builds query objects and renders
tables. (See primer 03 for the grammar, 04 for the priority score.)

## Header + batch-health strip
| UI element | Shows | Backend call |
|---|---|---|
| `budget 39/50` pill | daily LLM calls used | `GET /budget` |
| **Run extraction** button | batch-extract the CSV (cache-first) | `POST /extract/run` |
| "N notes aggregated" | rows in the view (non-review) | `POST /aggregate {group_by:[], measure:count}` |
| "N in review queue" | quarantined rows | `GET /review-queue` (length) |
| "N LLM calls left today" | remaining budget | `GET /budget` |

## Tab 1 — Defect Board (the headline)
- **What it is:** the money view — `subsystem × model × model_year` ranked by the priority score, so the
  CR-V infotainment cluster sits on top.
- **Query behind it:**
  ```json
  { "group_by": ["subsystem","model","model_year"],
    "measure": { "signal": "priority", "weights": {…} },
    "rank": { "by": "measure", "dir": "desc" } }
  ```
  → `POST /aggregate`. The in-row bar = the score magnitude (the honest "how big" cue).
- **Tune weights:** edits `measure.weights` and re-runs the same query — the ranking lens changes, the
  counts don't. Reset restores the severity-dominant default.
- **Click a row → drill-down:** `GET /extractions?subsystem=…&model=…`, then filtered to that `model_year`
  client-side → renders each note (below the table; it scrolls into view).

## Tab 2 — Explore (Query)
- **What it is:** the power surface — assign roles and get a ranked answer.
  - **Group by** (checkboxes) → `group_by` (order = nesting)
  - **Measure** → `count` / `priority` / `severity_index`
  - **Warranty / Flag / Model-year** → `filters` (year is a range; one bound is fine)
  - **Top-K** (needs exactly 2 group fields) → nested `top_k` (the CTE + `QUALIFY` path)
- **Backend:** the assembled query object → `POST /aggregate`. Same engine as the board.

## Tab 3 — Review Queue
- **What it is:** the honesty surface — low-confidence / validation-failed rows, **excluded from all
  aggregates by default**.
- **Backend:** `GET /review-queue` (records where `meta.needs_review = true`).

## The note detail (drill-down & review)
For one record it shows: complaint summary, chips (subsystem / warranty+denial / severity / resolution /
confidence), the true flags, the **source note with `evidence_quote` highlighted**, and the provenance line
(`schema · model · prompt · validation`). This is the audit view — every structured claim traces to the
note text.

## Why so thin
No analytics in the browser = the UI can't disagree with the API, everything is reproducible, and the same
`/aggregate` serves a future CLI, notebook, or NL layer. The dashboard is a *renderer*, not a second brain.
