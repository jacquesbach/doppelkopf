import { existsSync } from "node:fs";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { replaceSiteUrl, writeStaticFiles } from "./scripts/seo-build.mjs";
import { cleanSiteUrl } from "./src/lib/site.js";

// Suchmaschinen-Dateien: setzt die Domain (SITE_URL) in index.html ein und schreibt nach dem Build je Seite eine eigene HTML-Datei
// sowie robots.txt und sitemap.xml (siehe scripts/seo-build.mjs).
function seoPlugin(siteUrl) {
  let config;
  return {
    name: "doko-seo",
    configResolved(resolved) {
      config = resolved;
    },
    transformIndexHtml: (html) => replaceSiteUrl(html, siteUrl),
    closeBundle() {
      if (config?.command !== "build") return;
      const outDir = path.resolve(config.root, config.build.outDir);
      if (!existsSync(path.join(outDir, "index.html"))) return;   // Build fehlgeschlagen: nur die eigentliche Fehlermeldung zeigen
      const written = writeStaticFiles(outDir, siteUrl);
      config.logger.info(`SEO: ${written.join(", ")} (${siteUrl})`);
    },
  };
}

// Entwicklung: /api und /socket.io laufen ueber den Vite-Proxy zum Flask-Backend.
// Der Backend-Port kommt aus BACKEND_PORT (Umgebung oder .env im Projektordner), Standard 8181.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = `http://localhost:${process.env.BACKEND_PORT || env.BACKEND_PORT || 8181}`;
  // Domain der Website: SITE_URL (oder VITE_SITE_URL) aus Umgebung/.env, sonst https://doppelkopf.cc
  const siteUrl = cleanSiteUrl(process.env.SITE_URL || process.env.VITE_SITE_URL || env.SITE_URL || env.VITE_SITE_URL);
  return {
    plugins: [svelte(), seoPlugin(siteUrl)],
    define: { "import.meta.env.VITE_SITE_URL": JSON.stringify(siteUrl) },
    server: {
      port: 5173,
      proxy: {
        "/api": backend,
        "/socket.io": { target: backend, ws: true },
      },
    },
  };
});
