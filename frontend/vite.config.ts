import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies REST and WebSocket traffic to the FastAPI backend.
const backend = process.env.SAFEGUARD_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": { target: backend, changeOrigin: true, ws: true } },
  },
  preview: {
    port: 4173,
    proxy: { "/api": { target: backend, changeOrigin: true, ws: true } },
  },
  build: { chunkSizeWarningLimit: 1600 },
});
