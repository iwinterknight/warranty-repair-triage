import { useState } from "react";
import NoteDetail from "./NoteDetail.jsx";

// The "excel-like" audit view: every verbatim record behind a clicked aggregate row.
// Columns that DEFINE the cell or DRIVE the measure are highlighted; a row expands to the full detail
// (with evidence_quote highlighted in the note). Export CSV for the literal spreadsheet.
const COLS = ["note_id", "model", "model_year", "mileage", "subsystem",
              "warranty_status", "severity", "flags", "technician_note"];

const val = (r, k) => r.passthrough?.[k] ?? r.extraction?.[k];

function flagsOf(r) {
  const sf = r.extraction?.severity_flags;
  return sf && !Array.isArray(sf) ? Object.entries(sf).filter(([, v]) => v).map(([k]) => k) : [];
}

function cellText(r, c) {
  if (c === "flags") return flagsOf(r).join(", ") || "—";
  if (c === "technician_note") return r.technician_note || "";
  return String(val(r, c) ?? "—");
}

export default function ContributingRecords({ records, highlight, onClose }) {
  const [expanded, setExpanded] = useState(null);

  function exportCsv() {
    const esc = (s) => `"${String(s).replace(/"/g, '""')}"`;
    const body = records.map((r) => COLS.map((c) => esc(cellText(r, c))).join(",")).join("\n");
    const blob = new Blob([COLS.join(",") + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "contributing_records.csv";
    a.click();
  }

  return (
    <div className="panel">
      <h3>
        Contributing records ({records.length})
        <span className="muted"> — verbatim notes behind this row; highlighted = what drives it</span>
        <button className="btn ghost" style={{ float: "right" }} onClick={onClose}>Close</button>
        <button className="btn ghost" style={{ float: "right", marginRight: 8 }} onClick={exportCsv}>Export CSV</button>
      </h3>
      {records.length === 0 ? (
        <p className="muted">No records matched this row + the active filters.</p>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>{COLS.map((c) => <th key={c} className={highlight.has(c) ? "hl" : ""}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.note_id} className="click"
                    onClick={() => setExpanded(expanded === r.note_id ? null : r.note_id)}>
                  {COLS.map((c) => (
                    <td key={c}
                        className={`${highlight.has(c) ? "hl" : "dim"} ${c === "technician_note" ? "notecell" : ""}`}>
                      {cellText(r, c)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {expanded && <NoteDetail record={records.find((r) => r.note_id === expanded)} />}
    </div>
  );
}
