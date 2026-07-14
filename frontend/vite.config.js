import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server on :3000; VITE_API_URL points at the FastAPI backend (default :8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 3000, host: true },
});
