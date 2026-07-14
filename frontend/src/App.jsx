import { useEffect, useState } from "react";
import { api } from "./api.js";
import DefectBoard from "./components/DefectBoard.jsx";
import QueryPanel from "./components/QueryPanel.jsx";
import ReviewQueue from "./components/ReviewQueue.jsx";

const TABS = [
  ["board", "Defect Board"],
  ["explore", "Explore (Query)"],
  ["review", "Review Queue"],
];

export default function App() {
  const [tab, setTab] = useState("board");
  const [health, setHealth] = useState({ aggregated: "—", review: "—" });
  const [budget, setBudget] = useState(null);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState(null);

  async function refresh() {
    try {
      const [agg, review, bud] = await Promise.all([
        api.aggregate({ group_by: [], measure: { signal: "count" } }),
        api.reviewQueue(),
        api.budget(),
      ]);
      setHealth({ aggregated: agg.rows[0]?.measure ?? 0, review: review.length });
      setBudget(bud);
      setErr(null);
    } catch (e) {
      setErr("Backend not reachable — start the API (uvicorn) and LocalStack. " + e);
    }
  }
  useEffect(() => { refresh(); }, []);

  async function runExtraction() {
    setRunning(true);
    try { await api.extractRun(); await refresh(); }
    catch (e) { setErr(String(e)); }
    finally { setRunning(false); }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>Warranty &amp; Repair-Order Triage</h1>
        {budget && <span className="pill">budget {budget.used}/{budget.limit}</span>}
        <button className="btn" onClick={runExtraction} disabled={running}>
          {running ? "Extracting…" : "Run extraction"}
        </button>
      </div>

      <div className="strip">
        <div className="stat"><b>{health.aggregated}</b><span>notes aggregated</span></div>
        <div className="stat"><b>{health.review}</b><span>in review queue</span></div>
        {budget && <div className="stat"><b>{budget.remaining}</b><span>LLM calls left today</span></div>}
      </div>

      {err && <p className="err">{err}</p>}

      <div className="tabs">
        {TABS.map(([k, label]) => (
          <div key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{label}</div>
        ))}
      </div>

      {tab === "board" && <DefectBoard />}
      {tab === "explore" && <QueryPanel />}
      {tab === "review" && <ReviewQueue />}
    </div>
  );
}
