import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  const port = Number(env.VITE_PORT ?? 3100);
  const backendPort = Number(env.VITE_BACKEND_PORT ?? 8100);

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port,
      proxy: {
        // Proxy API routes so the browser can call same-origin paths.
        "/simulations": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
        "/health": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
        "/scenarios": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
        "/capabilities": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
        "/agent": {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});

