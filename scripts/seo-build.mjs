// Erzeugt nach dem Vite-Build die Dateien für Suchmaschinen (siehe vite.config.js):
//  - je indexierbarer Seite eine eigene HTML-Datei mit passendem Titel, Beschreibung, canonical, robots und Klartext-Inhalt,
//    damit auch Crawler ohne JavaScript (und Link-Vorschauen) das Richtige sehen,
//  - app.html: neutrale Hülle (noindex) für Tisch, Beitreten, Admin und für Fehlerseiten,
//  - robots.txt und sitemap.xml mit der Domain aus SITE_URL.
// Alle Funktionen sind rein (Text rein, Text raus) und in tests/seo.test.js getestet. Nur writeStaticFiles schreibt Dateien.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { PAGES, isIndexable, seoForKey } from "../src/lib/seo.js";
import { RULES, RULES_LEAD, RULES_TITLE } from "../src/content/rules.js";
import { FAQ, FAQ_TITLE, HOME_FEATURES, HOME_H1, HOME_LEAD } from "../src/content/home.js";
import { GITHUB_URL } from "../src/lib/site.js";

// Seite (Schlüssel in PAGES) → Datei im Build-Ordner. nginx liefert sie ohne Weiterleitung aus (deploy/nginx.conf).
export const STATIC_PAGES = [
  { key: "landing", file: "index.html" },
  { key: "rules", file: "regeln/index.html" },
  { key: "impressum", file: "impressum/index.html" },
  { key: "datenschutz", file: "datenschutz/index.html" },
  { key: "shell", file: "app.html" },
];

const esc = (text) =>
  String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const escRe = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Ersetzt den Platzhalter für die Domain (Startseite-Vorlage index.html). */
export function replaceSiteUrl(html, siteUrl) {
  return html.replaceAll("%SITE_URL%", siteUrl);
}

// --- HTML-Bausteine ------------------------------------------------------------------------------------------------------

function blocksToHtml(blocks) {
  return blocks
    .map((block) => {
      switch (block.type) {
        case "h2": return `<h2>${esc(block.text)}</h2>`;
        case "h3": return `<h3>${esc(block.text)}</h3>`;
        case "p": return `<p>${esc(block.text)}</p>`;
        case "ul": return `<ul>${block.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
        case "ol": return `<ol>${block.items.map((i) => `<li>${esc(i)}</li>`).join("")}</ol>`;
        default: throw new Error(`Unbekannter Blocktyp: ${block.type}`);
      }
    })
    .join("\n");
}

const NAV =
  `<p><a href="/">Startseite</a> · <a href="/regeln">Spielregeln</a> · <a href="/neu">Tisch eröffnen</a> · ` +
  `<a href="/impressum">Impressum</a> · <a href="/datenschutz">Datenschutz</a> · ` +
  `<a href="${GITHUB_URL}" rel="noopener noreferrer">GitHub</a></p>`;
const NEEDS_JS = "<p>Zum Spielen braucht DOPPELKOPF.CC JavaScript. Bitte aktiviere es in deinem Browser.</p>";
const WRAP = 'style="max-width:760px;margin:0 auto;padding:24px;font:16px/1.6 system-ui,sans-serif;color:#000;background:#fffdf5"';

/** Klartext-Inhalt einer Seite für <noscript> (Suchmaschinen, Besucher ohne JavaScript). */
export function staticContent(key) {
  let body;
  switch (key) {
    case "landing":
      body = [
        `<h1>${esc(HOME_H1)}</h1>`,
        `<p>${esc(HOME_LEAD)}</p>`,
        `<ul>${HOME_FEATURES.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>`,
        `<h2>${esc(FAQ_TITLE)}</h2>`,
        FAQ.map((f) => `<h3>${esc(f.q)}</h3><p>${esc(f.a)}</p>`).join("\n"),
        NEEDS_JS,
        NAV,
      ].join("\n");
      break;
    case "rules":
      body = [`<h1>${esc(RULES_TITLE)}</h1>`, `<p>${esc(RULES_LEAD)}</p>`, blocksToHtml(RULES), NAV].join("\n");
      break;
    case "impressum":
      body = ["<h1>Impressum</h1>", "<p>Die Anbieterangaben werden per JavaScript geladen. Bitte aktiviere es in deinem Browser.</p>", NAV].join("\n");
      break;
    case "datenschutz":
      body = ["<h1>Datenschutzerklärung</h1>", "<p>Die Datenschutzerklärung wird per JavaScript geladen. Bitte aktiviere es in deinem Browser.</p>", NAV].join("\n");
      break;
    default:
      body = [NEEDS_JS, NAV].join("\n");
  }
  return `<div ${WRAP}>\n${body}\n</div>`;
}

// --- HTML umschreiben ----------------------------------------------------------------------------------------------------

function tagPattern(tag, attr, value) {
  return new RegExp(`<${tag}\\b[^>]*\\b${attr}=["']${escRe(value)}["'][^>]*>`);
}

function replaceOnce(html, pattern, replacement, what) {
  if (!pattern.test(html)) throw new Error(`index.html: ${what} nicht gefunden – scripts/seo-build.mjs und index.html passen nicht zusammen.`);
  return html.replace(pattern, () => replacement);
}

/** Stellt aus der gebauten index.html die Fassung einer Seite her. */
export function renderPage(html, key, siteUrl) {
  const meta = seoForKey(key, siteUrl);
  const q = esc(meta.title);
  const d = esc(meta.description);
  let out = html.replace(/<!--[\s\S]*?-->/g, "");   // Entwicklerkommentare nicht ausliefern
  out = replaceOnce(out, /<title>[\s\S]*?<\/title>/, `<title>${q}</title>`, "<title>");
  out = replaceOnce(out, tagPattern("meta", "name", "description"), `<meta name="description" content="${d}" />`, "meta description");
  out = replaceOnce(out, tagPattern("meta", "name", "robots"), `<meta name="robots" content="${esc(meta.robots)}" />`, "meta robots");
  out = replaceOnce(
    out,
    tagPattern("link", "rel", "canonical"),
    meta.canonical ? `<link rel="canonical" href="${esc(meta.canonical)}" />` : "",   // noindex-Seiten: keine canonical
    "link canonical",
  );
  out = replaceOnce(out, tagPattern("meta", "property", "og:title"), `<meta property="og:title" content="${q}" />`, "og:title");
  out = replaceOnce(out, tagPattern("meta", "property", "og:description"), `<meta property="og:description" content="${d}" />`, "og:description");
  out = replaceOnce(out, tagPattern("meta", "property", "og:url"), `<meta property="og:url" content="${esc(meta.url)}" />`, "og:url");
  out = replaceOnce(out, tagPattern("meta", "name", "twitter:title"), `<meta name="twitter:title" content="${q}" />`, "twitter:title");
  out = replaceOnce(out, tagPattern("meta", "name", "twitter:description"), `<meta name="twitter:description" content="${d}" />`, "twitter:description");
  out = replaceOnce(
    out,
    /<noscript\b[^>]*\bid=["']static-content["'][^>]*>[\s\S]*?<\/noscript>/,
    `<noscript id="static-content">\n${staticContent(key)}\n</noscript>`,
    "noscript#static-content",
  );
  return out.replace(/\n\s*\n+/g, "\n");
}

// --- robots.txt und sitemap.xml ------------------------------------------------------------------------------------------

export function robotsTxt(siteUrl) {
  return [
    "User-agent: *",
    "Allow: /",
    "Disallow: /api/",
    "Disallow: /socket.io/",
    "",
    `Sitemap: ${siteUrl}/sitemap.xml`,
    "",
  ].join("\n");
}

/** Nur Seiten, die in den Index sollen (Startseite, Regeln). Tisch-, Admin- und Rechtsseiten sind noindex. */
export function sitemapXml(siteUrl) {
  const urls = Object.values(PAGES)
    .filter((page) => isIndexable(page.robots))
    .map((page) => `  <url><loc>${esc(siteUrl + (page.path === "/" ? "/" : page.path))}</loc></url>`);
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join("\n")}\n</urlset>\n`;
}

// --- alles zusammen ------------------------------------------------------------------------------------------------------

/** Dateiname (relativ zum Build-Ordner) → Inhalt. */
export function buildStaticFiles(indexHtml, siteUrl) {
  const files = {};
  for (const { key, file } of STATIC_PAGES) files[file] = renderPage(indexHtml, key, siteUrl);
  files["robots.txt"] = robotsTxt(siteUrl);
  files["sitemap.xml"] = sitemapXml(siteUrl);
  return files;
}

export function writeStaticFiles(distDir, siteUrl) {
  const indexHtml = readFileSync(join(distDir, "index.html"), "utf8");
  const files = buildStaticFiles(indexHtml, siteUrl);
  for (const [name, content] of Object.entries(files)) {
    const target = join(distDir, name);
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, content, "utf8");
  }
  return Object.keys(files);
}
