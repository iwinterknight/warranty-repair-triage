import { useState } from "react";
import { api } from "../api.js";
import ResultTable from "./ResultTable.jsx";

// The power surface: assign roles (Group / Filter / Measure) and get a ranked answer — same engine as presets.
const DIMENSIONS = ["subsystem", "model", "model_year", "warranty_status", "resolution_status", "severity"];
const FLAGS = ["safety_related", "repeat_visit", "intermittent", "fleet_signal", "customer_distress", "vehicle_disabled"];
const MEASURES = ["count", "priority", "severity_index", "avg_mileage"];

export default function QueryPanel() {
  const [groupBy, setGroupBy] = useState(["subsystem", "model"]);
  const [measure, setMeasure] = useState("count");
  const [warranty, setWarranty] = useState("");
  const [flag, setFlag] = useState("");
  const [yearMin, setYearMin] = useState("");
  const [yearMax, setYearMax] = useState("");
  const [mileageMin, setMileageMin] = useState("");
  const [mileageMax, setMileageMax] = useState("");
  const [topK, setTopK] = useState("");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  const toggleGroup = (d) =>
    setGroupBy((g) => (g.includes(d) ? g.filter((x) => x !== d) : [...g, d]));

  async function run() {
    setErr(null);
    const filters = {};
    if (warranty) filters.warranty_status = warranty;
    if (flag) filters.flags = { [flag]: true };
    // One-sided is fine: an empty bound becomes an open end of the range (BETWEEN 0..9999).
    if (yearMin || yearMax) filters.model_year = [Number(yearMin) || 0, Number(yearMax) || 9999];
    if (mileageMin || mileageMax) filters.mileage = [Number(mileageMin) || 0, Number(mileageMax) || 1000000];
    const query = { group_by: groupBy, filters, measure: { signal: measure }, rank: { by: "measure", dir: "desc" } };
    if (topK && groupBy.length === 2) query.top_k = { [groupBy[0]]: Number(topK), [groupBy[1]]: 3 };
    try {
      setResult(await api.aggregate(query));
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div>
      <div className="panel">
        <h3>Build a query — Group / Filter / Measure</h3>
        <div className="row">
          <div className="col">
            <label className="f">Group by (order = nesting)</label>
            {DIMENSIONS.map((d) => (
              <label key={d} style={{ display: "inline-block", marginRight: 10, fontSize: 13 }}>
                <input type="checkbox" style={{ width: "auto", marginRight: 4 }}
                  checked={groupBy.includes(d)} onChange={() => toggleGroup(d)} />
                {d}
              </label>
            ))}
          </div>
        </div>
        <div className="row">
          <div className="col"><label className="f">Measure</label>
            <select value={measure} onChange={(e) => setMeasure(e.target.value)}>
              {MEASURES.map((m) => <option key={m}>{m}</option>)}
            </select>
          </div>
          <div className="col"><label className="f">Warranty filter</label>
            <select value={warranty} onChange={(e) => setWarranty(e.target.value)}>
              <option value="">(any)</option>
              {["covered", "denied", "undetermined", "not_applicable"].map((w) => <option key={w}>{w}</option>)}
            </select>
          </div>
          <div className="col"><label className="f">Flag filter</label>
            <select value={flag} onChange={(e) => setFlag(e.target.value)}>
              <option value="">(any)</option>
              {FLAGS.map((f) => <option key={f}>{f}</option>)}
            </select>
          </div>
        </div>
        <div className="row">
          <div className="col"><label className="f">Model year ≥</label>
            <input value={yearMin} onChange={(e) => setYearMin(e.target.value)} placeholder="2020" /></div>
          <div className="col"><label className="f">Model year ≤</label>
            <input value={yearMax} onChange={(e) => setYearMax(e.target.value)} placeholder="2023" /></div>
          <div className="col"><label className="f">Top-K (needs exactly 2 group fields)</label>
            <input value={topK} onChange={(e) => setTopK(e.target.value)} placeholder="10" /></div>
        </div>
        <div className="row">
          <div className="col"><label className="f">Mileage ≥</label>
            <input value={mileageMin} onChange={(e) => setMileageMin(e.target.value)} placeholder="0" /></div>
          <div className="col"><label className="f">Mileage ≤</label>
            <input value={mileageMax} onChange={(e) => setMileageMax(e.target.value)} placeholder="20000" /></div>
          <div className="col" />
        </div>
        <button className="btn" style={{ marginTop: 12 }} onClick={run}>Run query</button>
        {err && <p className="err">{err}</p>}
      </div>
      {result && <div className="panel"><ResultTable result={result} /></div>}
    </div>
  );
}
