import { useEffect, useState } from "react";
import { api } from "../api.js";
import ResultTable from "./ResultTable.jsx";
import WeightsPanel, { DEFAULT_WEIGHTS } from "./WeightsPanel.jsx";
import NoteDetail from "./NoteDetail.jsx";

// The headline: subsystem × model × model_year ranked by the (tunable) priority score.
export default function DefectBoard() {
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [result, setResult] = useState(null);
  const [cellNotes, setCellNotes] = useState(null);
  const [showWeights, setShowWeights] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api
      .aggregate({
        group_by: ["subsystem", "model", "model_year"],
        measure: { signal: "priority", weights },
        rank: { by: "measure", dir: "desc" },
      })
      .then(setResult)
      .catch((e) => setErr(String(e)));
  }, [weights]);

  async function openCell(row) {
    const recs = await api.extractions({ subsystem: row.subsystem, model: row.model });
    setCellNotes(recs.filter((r) => String(r.passthrough?.model_year) === String(row.model_year)));
  }

  return (
    <div>
      <div className="panel">
        <h3>
          Defect concentration — what's failing &amp; clustering
          <button className="btn ghost" style={{ float: "right" }} onClick={() => setShowWeights((v) => !v)}>
            {showWeights ? "Hide" : "Tune"} weights
          </button>
        </h3>
        {err && <p className="err">{err}</p>}
        <ResultTable result={result} onRowClick={openCell} />
        <p className="muted" style={{ marginTop: 8 }}>
          Ranked by a severity-dominant priority score. Click a row to drill into its notes. n shown per cell via the bar.
        </p>
      </div>

      {showWeights && <WeightsPanel weights={weights} onChange={setWeights} />}

      {cellNotes && (
        <div className="panel">
          <h3>
            Notes in this cell ({cellNotes.length})
            <button className="btn ghost" style={{ float: "right" }} onClick={() => setCellNotes(null)}>Close</button>
          </h3>
          {cellNotes.map((r) => <NoteDetail key={r.note_id} record={r} />)}
        </div>
      )}
    </div>
  );
}
