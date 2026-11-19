import { defineConfig, loadEnv } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// Entwicklung: /api und /socket.io laufen ueber den Vite-Proxy zum Flask-Backend.
// Der Backend-Port kommt aus BACKEND_PORT (Umgebung oder .env im Projektordner), Standard 8181.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = `http://localhost:${process.env.BACKEND_PORT || env.BACKEND_PORT || 8181}`;
  return {
    plugins: [svelte()],
    server: {
      port: 5173,
      proxy: {
        "/api": backend,
        "/socket.io": { target: backend, ws: true },
      },
    },
  };
});
