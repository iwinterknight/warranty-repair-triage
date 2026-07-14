# Primer: Priority score (severity-dominant, tunable)   ·   ~5 min   ·   [Judgment]
> The one place the tool imposes an *opinion* — which cell floats to the top. Everything else is neutral
> counting; this is the judgment, so it's transparent and overridable.

## The concept (first principles)
Ranking needs a score, and a score is a value judgment. Ours is **severity-dominant** (ratified): a single
`critical`/`high` should be able to outrank a big pile of `low`/`medium`. The trick is a **steep severity
map** — `low=1, medium=4, high=16, critical=64` — so one `critical` (64) already outweighs 60 `low` notes.
Count and recency are secondary; `safety_related`/`repeat_visit`/`fleet_signal` are boosts.

Because it's an opinion, two rules apply: it's **transparent** (the formula is inspectable) and **tunable +
reset-to-default** (the analyst can reweight; weights ride in the query object). Tuning changes the *ranking
lens, not the counts*.

*Why it works on our data:* RO-100026 (CR-V Hybrid infotainment, `high` + `safety_related`) scores ~47 and
takes the #1 cell — exactly the safety-escalating signal an analyst must see first.

## Plain-English breakdown (for explaining it out loud)
The score adds up **four things**, per cell:

| Ingredient | Plain meaning | Number it produces |
|---|---|---|
| **severity** | how serious are these failures | each note scored `low=1/med=4/high=16/crit=64`, summed |
| **count (n)** | how many notes in this cell (the *intersection* of the group fields) | the note count |
| **recency** | how fresh — newest note's date vs the dataset's own oldest→newest span | `0..1` (1 = newest note in the data) |
| **flag boosts** | red flags | `+25` safety, `+5` repeat, `+8` fleet |

`score = w_sev·Σseverity + w_count·n + w_recency·recency + Σboosts`  (default dials: sev ×1, count ×1, recency ×5)

**Worked example — the #1 cell, RO-100026 (CR-V Hybrid infotainment, `high` + `safety_related`, newest note):**
`16 (high severity) + 1 (one note) + 5 (recency 1.0 × 5) + 25 (safety boost) = 47`. High not because of
volume (n=1) but because it's serious, safety-flagged, and brand-new — exactly what to triage first.
The decimal tails you see (e.g. `5.9`) are the recency term (rarely a whole number).

- A **note** = one repair-order row (30 in the sample). **Note count** = how many notes match the cell's
  group fields at once (e.g. `infotainment × CR-V = 4` = notes that are both).
- **Recency** uses `date` from the CSV: `1 − (newest_overall − cell_newest) / span_days`, span = oldest→newest
  across all notes (2026-04-08 → 2026-06-22 = 75 days). Anchored to the dataset, not "today", so it's
  deterministic/testable; production would anchor to now.
- **Plain counts instead?** use the `count` measure (Explore), or zero the sev/recency/boost dials.

## In the code
- `backend/query_engine.py` → `DEFAULT_WEIGHTS` — the severity-dominant defaults (the imposed opinion).
- `backend/query_engine.py` → `_priority_expr()` — the score as a SQL aggregate: `w_severity*Σseverity +
  w_count*count + w_recency*recency + boosts`. Weights are floats coerced in; tunable via
  `measure.weights` in the query object.
- `backend/query_engine.py` → `_sev_case()` — the steep severity→number map.
- `tests/test_aggregate.py` → `test_headline_cluster_ranks_first` — proves the intended cell wins.

## Why it's built this way
→ ADR-0005/0006 · SDD §7 (D refined by E). Default opinion + full tunability = **trust *and* control** —
resolves the "opinionated vs. neutral tool" tension. (Frontend exposes weights + Reset — core, not stretch.)

## Probe deeper? (pick your dive)
- 🔍 **`_priority_expr()` recency term** — computed from the dataset's own date span (not `today`), so it's
  deterministic and testable. Trace the `date_diff` / global-max subquery.
- 🔍 **Severity-dominance math** — why the steep `1/4/16/64` map (not linear) is what makes a lone
  `critical` outrank a cluster, and how you'd retune for a "volume-first" lens.
