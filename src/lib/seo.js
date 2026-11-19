// Suchmaschinen-Angaben je Seite (Titel, Beschreibung, robots, kanonische Adresse).
// Reine Funktionen ohne DOM-Zugriff: Der Browser (applySeo) und der Build (scripts/seo-build.mjs) nutzen dieselben Texte,
// damit das statische HTML und die per JavaScript gesetzten Angaben nie auseinanderlaufen.
import { SITE_NAME } from "./site.js";

export const ROBOTS_INDEX = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1";
export const ROBOTS_NOINDEX = "noindex, follow";
export const ROBOTS_PRIVATE = "noindex, nofollow";

export const PAGES = {
  landing: {
    path: "/",
    title: `Doppelkopf online spielen – kostenlos | ${SITE_NAME}`,
    description:
      "Doppelkopf online kostenlos spielen: nach DDV-Turnierregeln, mit Hausregeln, privaten Tischen per Link und Bots. Ohne Anmeldung, ohne Werbung.",
    robots: ROBOTS_INDEX,
  },
  rules: {
    path: "/regeln",
    title: `Doppelkopf-Regeln einfach erklärt | ${SITE_NAME}`,
    description:
      "Doppelkopf-Regeln kompakt: Karten und Trümpfe, Spielablauf, Re und Kontra, Ansagen, Sonderpunkte und Zählung nach den DDV-Turnierregeln.",
    robots: ROBOTS_INDEX,
  },
  impressum: {
    path: "/impressum",
    title: `Impressum | ${SITE_NAME}`,
    description: `Impressum und Anbieterkennzeichnung von ${SITE_NAME}.`,
    robots: ROBOTS_NOINDEX,
  },
  datenschutz: {
    path: "/datenschutz",
    title: `Datenschutzerklärung | ${SITE_NAME}`,
    description: `Datenschutzerklärung von ${SITE_NAME}: Welche Daten beim Spielen verarbeitet werden und welche Rechte du hast.`,
    robots: ROBOTS_NOINDEX,
  },
  // Dynamische Seiten (Tisch anlegen, beitreten, spielen, Betreiber) und Fehlerseiten: nie in den Index.
  create: { path: "/neu", title: `Neuen Tisch eröffnen | ${SITE_NAME}`, robots: ROBOTS_NOINDEX },
  join: { path: "/beitreten", title: `Tisch beitreten | ${SITE_NAME}`, robots: ROBOTS_NOINDEX },
  table: { path: "/tisch", title: `Doppelkopf-Tisch | ${SITE_NAME}`, robots: ROBOTS_PRIVATE },
  admin: { path: "/admin", title: `Betreiber | ${SITE_NAME}`, robots: ROBOTS_PRIVATE },
  notfound: { path: "/", title: `Seite nicht gefunden | ${SITE_NAME}`, robots: ROBOTS_PRIVATE },
  // Statische Hülle (app.html) für alle dynamischen Adressen, bevor JavaScript den richtigen Titel setzt.
  shell: { path: "/", title: `Doppelkopf online | ${SITE_NAME}`, robots: ROBOTS_PRIVATE },
};

const FALLBACK_DESCRIPTION = PAGES.landing.description;

/** Schlüssel in PAGES für eine Route aus router.js. */
export function pageKey(route) {
  switch (route?.name) {
    case "landing": return "landing";
    case "rules": return "rules";
    case "legal": return route.page === "datenschutz" ? "datenschutz" : "impressum";
    case "create": return "create";
    case "join": return "join";
    case "table": return "table";
    case "admin": return "admin";
    default: return "notfound";
  }
}

export function isIndexable(robots) {
  return /^index\b/i.test(robots);
}

/** Titel, Beschreibung, robots und (nur für indexierbare Seiten) die kanonische Adresse. */
export function seoFor(route, siteUrl) {
  return seoForKey(pageKey(route), siteUrl);
}

export function seoForKey(key, siteUrl) {
  const page = PAGES[key];
  const indexable = isIndexable(page.robots);
  return {
    key,
    title: page.title,
    description: page.description ?? FALLBACK_DESCRIPTION,
    robots: page.robots,
    indexable,
    canonical: indexable ? `${siteUrl}${page.path === "/" ? "/" : page.path}` : null,
    url: `${siteUrl}${page.path === "/" ? "/" : page.path}`,
  };
}

function upsert(doc, selector, tag, attrs) {
  let el = doc.head.querySelector(selector);
  if (!el) {
    el = doc.createElement(tag);
    for (const [name, value] of Object.entries(attrs)) if (name !== "content" && name !== "href") el.setAttribute(name, value);
    doc.head.appendChild(el);
  }
  return el;
}

/** Schreibt die Angaben in <head> (Single-Page-App: nach jedem Seitenwechsel aufrufen). */
export function applySeo(route, siteUrl, doc = document) {
  const meta = seoFor(route, siteUrl);
  doc.title = meta.title;
  const setMeta = (attr, name, value) => upsert(doc, `meta[${attr}="${name}"]`, "meta", { [attr]: name }).setAttribute("content", value);
  setMeta("name", "description", meta.description);
  setMeta("name", "robots", meta.robots);
  setMeta("property", "og:title", meta.title);
  setMeta("property", "og:description", meta.description);
  setMeta("property", "og:url", meta.url);
  setMeta("name", "twitter:title", meta.title);
  setMeta("name", "twitter:description", meta.description);
  const canonical = doc.head.querySelector('link[rel="canonical"]');
  if (meta.canonical) upsert(doc, 'link[rel="canonical"]', "link", { rel: "canonical" }).setAttribute("href", meta.canonical);
  else canonical?.remove();   // noindex-Seiten brauchen keine kanonische Adresse (sie widerspräche dem noindex)
  return meta;
}
