// Thin client over the FastAPI backend. All analytics go through /aggregate (one query object).
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function j(path, opts) {
  const r = await fetch(BASE + path, opts);
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

function qs(params = {}) {
  const s = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== null && v !== undefined)
  ).toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => j("/health"),
  budget: () => j("/budget"),
  presets: () => j("/presets"),
  aggregate: (query) =>
    j("/aggregate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    }),
  extractions: (params) => j("/extractions" + qs(params)),
  extraction: (id) => j(`/extractions/${id}`),
  reviewQueue: () => j("/review-queue"),
  extractRun: () => j("/extract/run", { method: "POST" }),
  extractStatus: () => j("/extract/status"),
};
