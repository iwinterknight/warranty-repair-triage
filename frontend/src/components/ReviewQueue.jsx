import { useEffect, useState } from "react";
import { api } from "../api.js";
import NoteDetail from "./NoteDetail.jsx";

// The honesty surface: low-confidence / validation-failed rows, excluded from aggregates by default.
export default function ReviewQueue() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.reviewQueue().then(setRows).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <p className="err">{err}</p>;
  if (!rows) return <p className="muted">Loading…</p>;

  return (
    <div className="panel">
      <h3>Review queue ({rows.length}) <span className="muted">— quarantined, not counted in aggregates</span></h3>
      {rows.length === 0 ? (
        <p className="muted">Nothing in review — every note validated.</p>
      ) : (
        rows.map((r) => <NoteDetail key={r.note_id} record={r} />)
      )}
    </div>
  );
}
