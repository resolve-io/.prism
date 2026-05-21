import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

const BACKEND = process.env.PRISM_BACKEND_URL ?? "http://127.0.0.1:7778";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
    dedupe: [
      "react",
      "react-dom",
      "@react-three/fiber",
      "@observablehq/plot",
      "three",
      "leva",
      "gsap",
    ],
  },
  build: {
    outDir: "../web_dist",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": { target: BACKEND, ws: true },
      "/sse": { target: BACKEND, ws: true },
      "/graph": { target: BACKEND },
    },
  },
});
