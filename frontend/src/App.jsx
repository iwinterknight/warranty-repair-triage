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
  const [progress, setProgress] = useState(null); // live batch progress (polled)
  const [tick, setTick] = useState(0);            // bumps to make the board re-fetch during a batch
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

  // Poll batch progress every 3s (catches runs started from the UI or curl). While a batch is active,
  // refresh the strip and bump `tick` so the board re-queries — the dashboard fills in live.
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const p = await api.extractStatus();
        if (p.active) {
          setProgress(p);
          setTick((t) => t + 1);
          refresh();
        } else {
          setProgress((prev) => {
            if (prev) { setTick((t) => t + 1); refresh(); }  // final refresh when a batch ends
            return null;
          });
        }
      } catch { /* backend unreachable — the strip already shows the error */ }
    }, 3000);
    return () => clearInterval(id);
  }, []);

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
        <button className="btn" onClick={runExtraction} disabled={running || !!progress}>
          {progress ? `Extracting… ${progress.done}/${progress.total}` : running ? "Extracting…" : "Run extraction"}
        </button>
      </div>

      <div className="strip">
        <div className="stat"><b>{health.aggregated}</b><span>notes aggregated</span></div>
        <div className="stat"><b>{health.review}</b><span>in review queue</span></div>
        {budget && <div className="stat"><b>{budget.remaining}</b><span>LLM calls left today</span></div>}
      </div>

      {progress && (
        <div className="panel" style={{ padding: "10px 14px" }}>
          Extracting notes — <b>{progress.done} of {progress.total}</b> processed
          {progress.from_cache > 0 && <span className="muted"> · {progress.from_cache} served from cache</span>}
          {progress.needs_review > 0 && <span className="muted"> · {progress.needs_review} sent to review</span>}
          {progress.failed > 0 && <span className="muted"> · {progress.failed} hit provider limits — will retry free on the next run</span>}
          <div style={{ height: 6, background: "var(--border)", borderRadius: 3, marginTop: 8 }}>
            <div style={{ height: 6, borderRadius: 3, background: "var(--accent)", transition: "width .4s",
                          width: `${(progress.done / Math.max(1, progress.total)) * 100}%` }} />
          </div>
        </div>
      )}

      {err && <p className="err">{err}</p>}

      <div className="tabs">
        {TABS.map(([k, label]) => (
          <div key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{label}</div>
        ))}
      </div>

      {tab === "board" && <DefectBoard tick={tick} />}
      {tab === "explore" && <QueryPanel />}
      {tab === "review" && <ReviewQueue />}
    </div>
  );
}
