import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // Allow the dev server to be reached over a shared tunnel / port-forward
    // (e.g. VS Code Port Forwarding *.devtunnels.ms, ngrok, cloudflared).
    // Vite 6 otherwise rejects unknown Host headers with "Blocked request".
    allowedHosts: [
      ".devtunnels.ms",
      ".ngrok-free.app",
      ".ngrok.app",
      ".trycloudflare.com",
    ],
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8020",
        changeOrigin: true,
        // AI generation can take minutes; keep the proxy connection open.
        timeout: 600000,
        proxyTimeout: 600000,
      },
    },
  },
});
