// Transparent, tunable, resettable priority-score weights (core — the one imposed opinion).
// Mirrors backend DEFAULT_WEIGHTS; changing a weight re-runs the board (ranking lens, not the counts).
export const DEFAULT_WEIGHTS = {
  severity_map: { low: 1, medium: 4, high: 16, critical: 64 },
  w_severity: 1, w_count: 1, w_recency: 5,
  boost_safety: 25, boost_repeat: 5, boost_fleet: 8,
};

const SCALARS = [
  ["w_severity", "severity weight"], ["w_count", "count weight"], ["w_recency", "recency weight"],
  ["boost_safety", "safety boost"], ["boost_repeat", "repeat boost"], ["boost_fleet", "fleet boost"],
];
const SEVS = ["low", "medium", "high", "critical"];

export default function WeightsPanel({ weights, onChange }) {
  const setScalar = (k, v) => onChange({ ...weights, [k]: Number(v) });
  const setSev = (s, v) =>
    onChange({ ...weights, severity_map: { ...weights.severity_map, [s]: Number(v) } });

  return (
    <div className="panel">
      <h3>
        Priority weights <span className="muted">— the one imposed opinion (severity-dominant default)</span>
        <button className="btn ghost" style={{ float: "right" }} onClick={() => onChange(DEFAULT_WEIGHTS)}>
          Reset to default
        </button>
      </h3>
      <div className="wgrid">
        {SEVS.map((s) => (
          <div key={s}>
            <label className="f">severity: {s}</label>
            <input type="number" value={weights.severity_map[s]} onChange={(e) => setSev(s, e.target.value)} />
          </div>
        ))}
        {SCALARS.map(([k, label]) => (
          <div key={k}>
            <label className="f">{label}</label>
            <input type="number" value={weights[k]} onChange={(e) => setScalar(k, e.target.value)} />
          </div>
        ))}
      </div>
    </div>
  );
}
