import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import ResultTable from "./ResultTable.jsx";
import HeatmapView from "./HeatmapView.jsx";
import WeightsPanel, { DEFAULT_WEIGHTS } from "./WeightsPanel.jsx";
import NoteDetail from "./NoteDetail.jsx";

// Preset groupings. Fewer dims = the cluster merges into one cell (e.g. all CR-V infotainment years).
const GROUPINGS = {
  "subsystem × model × year": ["subsystem", "model", "model_year"],
  "subsystem × model": ["subsystem", "model"],
  "subsystem × year": ["subsystem", "model_year"],
  "subsystem": ["subsystem"],
  "model × subsystem": ["model", "subsystem"],
};

// where a group field lives on a record
const val = (r, key) => r.passthrough?.[key] ?? r.extraction?.[key];

export default function DefectBoard() {
  const [groupKey, setGroupKey] = useState("subsystem × model × year");
  const [view, setView] = useState("table"); // "table" | "heat"
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [result, setResult] = useState(null);
  const [cellNotes, setCellNotes] = useState(null);
  const [showWeights, setShowWeights] = useState(false);
  const [err, setErr] = useState(null);
  const drillRef = useRef(null);

  const groupBy = GROUPINGS[groupKey];
  const canHeat = groupBy.length === 2;
  const showHeat = view === "heat" && canHeat;

  useEffect(() => {
    if (cellNotes && drillRef.current) drillRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [cellNotes]);

  // Two aggregates over the same grouping — priority (ranking) + avg mileage (context) — merged per cell.
  // Mileage matters: the CR-V cluster is a *low-mileage* signal, so surfacing it per cell is analytically real.
  useEffect(() => {
    setCellNotes(null);
    const keyOf = (r) => groupBy.map((g) => r[g]).join("|");
    Promise.all([
      api.aggregate({ group_by: groupBy, measure: { signal: "priority", weights }, rank: { by: "measure", dir: "desc" } }),
      api.aggregate({ group_by: groupBy, measure: { signal: "avg_mileage" } }),
    ])
      .then(([pri, mil]) => {
        const mmap = {};
        mil.rows.forEach((r) => { mmap[keyOf(r)] = r.measure; });
        const rows = pri.rows.map((r) => ({ ...r, avg_mileage: mmap[keyOf(r)] ?? null }));
        setResult({ columns: [...groupBy, "avg_mileage", "measure"], rows });
      })
      .catch((e) => setErr(String(e)));
  }, [groupKey, weights]);

  // Heatmap needs exactly 2 group fields; if we're not there, collapse to subsystem × model so one click
  // always yields a heatmap instead of a dead/disabled button.
  function toggleHeat() {
    if (showHeat) return setView("table");
    if (groupBy.length !== 2) setGroupKey("subsystem × model");
    setView("heat");
  }

  // Drill-down: fetch by subsystem/model when present, then match every grouped field client-side.
  async function openCell(row) {
    const params = {};
    if (row.subsystem) params.subsystem = row.subsystem;
    if (row.model) params.model = row.model;
    const recs = await api.extractions(params);
    setCellNotes(recs.filter((r) => groupBy.every((g) => String(val(r, g)) === String(row[g]))));
  }

  return (
    <div>
      <div className="panel">
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
          <h3 style={{ margin: 0, flex: 1 }}>Defect concentration — what's failing &amp; clustering</h3>
          <label className="f" style={{ margin: 0 }}>Group by</label>
          <select value={groupKey} onChange={(e) => setGroupKey(e.target.value)} style={{ width: "auto" }}>
            {Object.keys(GROUPINGS).map((k) => <option key={k}>{k}</option>)}
          </select>
          <button className="btn ghost" onClick={toggleHeat}>
            {showHeat ? "Table" : "Heatmap"} view
          </button>
          <button className="btn ghost" onClick={() => setShowWeights((v) => !v)}>
            {showWeights ? "Hide" : "Tune"} weights
          </button>
        </div>
        {err && <p className="err">{err}</p>}
        {showHeat
          ? <HeatmapView result={result} gRow={groupBy[0]} gCol={groupBy[1]}
              onCell={(rk, ck) => openCell({ [groupBy[0]]: rk, [groupBy[1]]: ck })} />
          : <ResultTable result={result} onRowClick={openCell} />}
        <p className="muted" style={{ marginTop: 8 }}>
          Ranked by a severity-dominant priority score. Fewer group fields merge the cluster into one cell.
          Click a {showHeat ? "cell" : "row"} to drill into its notes.
        </p>
      </div>

      {showWeights && <WeightsPanel weights={weights} onChange={setWeights} />}

      {cellNotes && (
        <div className="panel" ref={drillRef}>
          <h3>
            Notes in this cell ({cellNotes.length})
            <button className="btn ghost" style={{ float: "right" }} onClick={() => setCellNotes(null)}>Close</button>
          </h3>
          {cellNotes.length
            ? cellNotes.map((r) => <NoteDetail key={r.note_id} record={r} />)
            : <p className="muted">No notes matched this cell.</p>}
        </div>
      )}
    </div>
  );
}
