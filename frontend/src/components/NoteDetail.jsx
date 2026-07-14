// One extraction record: complaint, warranty, severity, flags, and the source note with evidence highlighted.
function Evidence({ note, quote }) {
  if (!note) return null;
  const i = quote ? note.indexOf(quote) : -1;
  if (i < 0) return <div className="note">{note}</div>;
  return (
    <div className="note">
      {note.slice(0, i)}
      <mark className="evidence">{note.slice(i, i + quote.length)}</mark>
      {note.slice(i + quote.length)}
    </div>
  );
}

export default function NoteDetail({ record }) {
  if (!record) return null;
  const e = record.extraction || {};
  const m = record.meta || {};
  // Guard: a misbehaving model can return severity_flags as an array; Object.entries would then yield
  // numeric index keys ("0", "1"…) and render bogus "0" chips. Only treat a plain object as flags.
  const sf = e.severity_flags && !Array.isArray(e.severity_flags) ? e.severity_flags : {};
  const flags = Object.entries(sf).filter(([, v]) => v).map(([k]) => k);

  return (
    <div className="panel">
      <h3>
        {record.note_id}{" "}
        <span className="muted">
          {record.passthrough?.model} {record.passthrough?.model_year} · {record.passthrough?.mileage} mi
        </span>
        {m.needs_review && <span className="chip warn" style={{ float: "right" }}>needs review</span>}
      </h3>
      <p>{e.complaint_summary}</p>
      <div style={{ margin: "8px 0" }}>
        <span className="chip">subsystem: {e.subsystem}</span>
        <span className="chip">warranty: {e.warranty_status}{e.denial_reason ? ` (${e.denial_reason})` : ""}</span>
        <span className={`chip sev-${e.severity}`}>severity: {e.severity}</span>
        <span className="chip">resolution: {e.resolution_status}</span>
        <span className="chip">confidence: {e.confidence}</span>
      </div>
      <div style={{ margin: "8px 0" }}>
        {flags.length ? flags.map((f) => <span key={f} className="chip">{f}</span>) : <span className="muted">no flags</span>}
      </div>
      <label className="f">source note (evidence highlighted)</label>
      <Evidence note={record.technician_note} quote={e.evidence_quote} />
      <p className="mono muted" style={{ marginTop: 8 }}>
        schema {m.schema_version} · model {m.model} · prompt {m.prompt_version} · {m.validation}
      </p>
    </div>
  );
}
