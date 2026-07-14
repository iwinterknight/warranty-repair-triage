# UI Talking Points (crib — not a deep primer)

Answers to have ready if they ask about the frontend / visuals. Keep it high-level; the real work is in the
backend, and the UI is a **thin client** that only renders what `POST /aggregate` returns.

## Why these visuals (match the mark to the data shape)
- **Heatmap** → 2-actor concentration (e.g. subsystem × model): the eye finds the dense/hot cell fast — how we *see* the CR-V cluster.
- **100% stacked bar** → categorical composition (warranty mix, resolution mix): shows share, not raw count.
- **Rate bars** → boolean flag prevalence (safety/repeat/intermittent %): "how often does this flag fire."
- **KPI cards** → population scalars (0 group-by): totals, severity index, needs_review count.
- **Ranked table** → any top-k / lookup query: charts can't *sort-and-nest* ("top-10 models × top-3 subsystems"). The table is the workhorse; charts are for gestalt.

## Why a table when data is thin
At n=30 many cells are 1–3 notes. A ranked table with explicit `n` is honest; a smooth heatmap would imply statistical mass we don't have. **Presentation matches the data's weight.**

## How it's built
- **React (Vite)** thin client; no computation in the frontend — it POSTs a query object and renders the tidy result.
- **Nivo** for charts (native heatmap + bar + treemap, sane defaults); **HTML/CSS** for the ranked table.
- One `renderResult(result, shape)` picks the component by *(# group-by fields, is-ranked)* — so there's **no bespoke per-chart code**; the result's shape decides the view.

## Two "why not" answers
- **Why Nivo, not Recharts?** Recharts has no native heatmap, and heatmap is core to the concentration view. Nivo covers heatmap+bar+treemap in one dependency.
- **Why not Streamlit?** The brief pins Next.js/React + separate frontend/backend containers; Streamlit fails both.

## The through-line
Presets, the query panel, and the visuals all speak the **same query object** and hit **one endpoint** — the UI is just three ways to build that object and one shape-driven renderer. Plus the weights panel: the priority score is **transparent, tunable, reset-to-default**.
