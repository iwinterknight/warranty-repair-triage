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
