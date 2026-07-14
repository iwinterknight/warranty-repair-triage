// Reusable ranked table for any {columns, rows} aggregate result.
// The "measure" column renders an in-row magnitude bar — the honest primary readout (table-first design).
export default function ResultTable({ result, onRowClick }) {
  if (!result) return null;
  const { columns, rows } = result;
  if (!rows.length) return <p className="muted">No rows for this query.</p>;

  const max = Math.max(...rows.map((r) => Number(r.measure) || 0), 1);

  return (
    <div className="tablewrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={onRowClick ? "click" : ""} onClick={() => onRowClick && onRowClick(r)}>
              {columns.map((c) => (
                <td key={c}>
                  {c === "measure" ? (
                    <>
                      <span className="bar" style={{ width: `${(Number(r.measure) / max) * 90 + 4}px` }} />
                      {Number(r.measure).toFixed(1)}
                    </>
                  ) : (
                    String(r[c] ?? "—")
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
