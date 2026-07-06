import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Builds into dist/, which the FastAPI backend serves. Dev server proxies the
// API to the local backend so SSE and REST work in the inner loop.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: { outDir: "dist" },
});
