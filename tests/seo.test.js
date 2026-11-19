import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PAGES, applySeo, isIndexable, pageKey, seoFor } from "../src/lib/seo.js";
import { DEFAULT_SITE_URL, cleanSiteUrl } from "../src/lib/site.js";
import { matchRoute } from "../src/lib/router.js";
import { STATIC_PAGES, buildStaticFiles, renderPage, replaceSiteUrl, robotsTxt, sitemapXml, staticContent } from "../scripts/seo-build.mjs";

const SITE = "https://doppelkopf.cc";
const read = (file) => readFileSync(new URL(`../${file}`, import.meta.url), "utf8");
// So sieht index.html nach dem Vite-Build aus: Domain eingesetzt, Skript/CSS in den Kopf eingefügt.
const built = () =>
  replaceSiteUrl(read("index.html"), SITE).replace("</head>", '<script type="module" crossorigin src="/assets/x.js"></script></head>');

test("Site-URL: Standardwert, Schrägstrich am Ende und ungültige Eingaben", () => {
  assert.equal(cleanSiteUrl("https://doppelkopf.cc/"), "https://doppelkopf.cc");
  assert.equal(cleanSiteUrl("  https://example.org  "), "https://example.org");
  assert.equal(cleanSiteUrl(""), DEFAULT_SITE_URL);
  assert.equal(cleanSiteUrl(undefined), DEFAULT_SITE_URL);
  assert.equal(cleanSiteUrl("https://example.org/pfad"), DEFAULT_SITE_URL);
  assert.equal(cleanSiteUrl("javascript:alert(1)"), DEFAULT_SITE_URL);
});

test("Routen → SEO-Schlüssel: jede Route aus dem Router hat Angaben", () => {
  const cases = {
    "/": "landing", "/regeln": "rules", "/impressum": "impressum", "/datenschutz": "datenschutz",
    "/neu": "create", "/beitreten": "join", "/beitreten/AB12": "join", "/tisch/AB12": "table", "/admin": "admin", "/xyz": "notfound",
  };
  for (const [path, key] of Object.entries(cases)) assert.equal(pageKey(matchRoute(path)), key, path);
});

test("Indexierbar sind nur Startseite und Regeln; alles andere noindex", () => {
  const indexable = Object.entries(PAGES).filter(([, p]) => isIndexable(p.robots)).map(([k]) => k);
  assert.deepEqual(indexable.sort(), ["landing", "rules"]);
  for (const key of ["create", "join", "table", "admin", "notfound", "shell", "impressum", "datenschutz"]) {
    assert.match(PAGES[key].robots, /^noindex/, key);
  }
  for (const key of ["table", "admin"]) assert.match(PAGES[key].robots, /nofollow/, key);
});

test("Titel und Beschreibungen: eindeutig und in sinnvoller Länge", () => {
  const titles = new Set();
  const descriptions = new Set();
  for (const key of ["landing", "rules", "impressum", "datenschutz"]) {
    const meta = seoFor(matchRoute(PAGES[key].path), SITE);
    assert.ok(meta.title.length >= 20 && meta.title.length <= 65, `${key}: Titel ${meta.title.length} Zeichen`);
    assert.ok(meta.description.length >= 50 && meta.description.length <= 160, `${key}: Beschreibung ${meta.description.length} Zeichen`);
    titles.add(meta.title);
    descriptions.add(meta.description);
  }
  assert.equal(titles.size, 4);
  assert.equal(descriptions.size, 4);
  assert.match(PAGES.landing.title, /Doppelkopf online spielen/);
});

test("seoFor: canonical nur für indexierbare Seiten, ohne doppelten Schrägstrich", () => {
  assert.equal(seoFor({ name: "landing" }, SITE).canonical, "https://doppelkopf.cc/");
  assert.equal(seoFor({ name: "rules" }, SITE).canonical, "https://doppelkopf.cc/regeln");
  assert.equal(seoFor({ name: "legal", page: "impressum" }, SITE).canonical, null);
  assert.equal(seoFor({ name: "table", code: "AB12" }, SITE).canonical, null);
});

// Kleine DOM-Attrappe: genug für applySeo
function fakeDoc() {
  const head = {
    children: [],
    appendChild(el) { this.children.push(el); el.parentNode = this; },
    querySelector(sel) {
      const m = /^(\w+)\[(\w+)="([^"]+)"\]$/.exec(sel);
      return this.children.find((c) => c.tag === m[1] && c.attrs[m[2]] === m[3]) ?? null;
    },
  };
  const make = (tag) => ({
    tag, attrs: {},
    setAttribute(k, v) { this.attrs[k] = v; },
    remove() { head.children = head.children.filter((c) => c !== this); },
  });
  return { head, title: "", createElement: make };
}

test("applySeo setzt Titel, Beschreibung, robots, og:* und entfernt canonical bei noindex", () => {
  const doc = fakeDoc();
  applySeo({ name: "rules" }, SITE, doc);
  assert.match(doc.title, /Regeln/);
  assert.equal(doc.head.querySelector('link[rel="canonical"]').attrs.href, "https://doppelkopf.cc/regeln");
  assert.match(doc.head.querySelector('meta[name="robots"]').attrs.content, /^index/);
  assert.equal(doc.head.querySelector('meta[property="og:url"]').attrs.content, "https://doppelkopf.cc/regeln");
  applySeo({ name: "table", code: "AB12" }, SITE, doc);
  assert.equal(doc.head.querySelector('link[rel="canonical"]'), null);
  assert.equal(doc.head.querySelector('meta[name="robots"]').attrs.content, "noindex, nofollow");
});

test("Build: jede Seite bekommt eigenen Titel, canonical, robots und Klartext", () => {
  const files = buildStaticFiles(built(), SITE);
  assert.deepEqual(Object.keys(files).sort(), [...STATIC_PAGES.map((p) => p.file), "robots.txt", "sitemap.xml"].sort());

  const home = files["index.html"];
  assert.match(home, /<title>Doppelkopf online spielen – kostenlos \| DOPPELKOPF\.CC<\/title>/);
  assert.match(home, /<link rel="canonical" href="https:\/\/doppelkopf\.cc\/" \/>/);
  assert.match(home, /<h1>Doppelkopf online spielen<\/h1>/);
  assert.match(home, /Ist DOPPELKOPF\.CC kostenlos\?/);
  assert.match(home, /<script type="module" crossorigin src="\/assets\/x\.js">/);   // Vite-Einträge bleiben erhalten

  const rules = files["regeln/index.html"];
  assert.match(rules, /<title>Doppelkopf-Regeln einfach erklärt \| DOPPELKOPF\.CC<\/title>/);
  assert.match(rules, /<link rel="canonical" href="https:\/\/doppelkopf\.cc\/regeln" \/>/);
  assert.match(rules, /<h2>Trumpf im Normalspiel<\/h2>/);
  assert.match(rules, /<meta property="og:url" content="https:\/\/doppelkopf\.cc\/regeln" \/>/);

  for (const file of ["impressum/index.html", "datenschutz/index.html", "app.html"]) {
    assert.doesNotMatch(files[file], /rel="canonical"/, file);
    assert.match(files[file], /name="robots" content="noindex/, file);
  }
  assert.doesNotMatch(files["index.html"], /<!--/);   // Entwicklerkommentare werden entfernt
  assert.doesNotMatch(files["index.html"], /%SITE_URL%/);
});

test("Build: fremde Domain wird überall eingesetzt, nichts von doppelkopf.cc bleibt übrig", () => {
  const other = "https://example.org";
  const html = replaceSiteUrl(read("index.html"), other);
  for (const [name, content] of Object.entries(buildStaticFiles(html, other))) {
    if (name === "app.html" || name.startsWith("impressum") || name.startsWith("datenschutz")) {
      assert.doesNotMatch(content, /doppelkopf\.cc\//, name);   // Domain nur als Textmarke DOPPELKOPF.CC erlaubt
    }
  }
  assert.match(robotsTxt(other), /Sitemap: https:\/\/example\.org\/sitemap\.xml/);
  assert.match(sitemapXml(other), /<loc>https:\/\/example\.org\/regeln<\/loc>/);
});

test("Build bricht laut ab, wenn index.html und Skript nicht zusammenpassen", () => {
  assert.throws(() => renderPage("<html><head></head><body></body></html>", "landing", SITE), /nicht gefunden/);
});

test("robots.txt und sitemap.xml", () => {
  const robots = robotsTxt(SITE);
  assert.match(robots, /^User-agent: \*$/m);
  assert.match(robots, /^Allow: \/$/m);
  assert.match(robots, /^Disallow: \/api\/$/m);
  assert.match(robots, /^Disallow: \/socket\.io\/$/m);
  assert.doesNotMatch(robots, /Disallow: \/(neu|tisch|admin|beitreten)/);   // noindex per Header: Crawler müssen die Seite lesen dürfen
  assert.match(robots, /^Sitemap: https:\/\/doppelkopf\.cc\/sitemap\.xml$/m);
  const sitemap = sitemapXml(SITE);
  assert.match(sitemap, /<loc>https:\/\/doppelkopf\.cc\/<\/loc>/);
  assert.match(sitemap, /<loc>https:\/\/doppelkopf\.cc\/regeln<\/loc>/);
  assert.doesNotMatch(sitemap, /impressum|datenschutz|tisch|admin|neu|beitreten/);
});

test("Klartext-Inhalt: HTML wird maskiert und enthält interne Links für Crawler", () => {
  const html = staticContent("rules");
  assert.match(html, /<a href="\/impressum">/);
  assert.match(html, /<a href="\/datenschutz">/);
  assert.match(html, /<a href="https:\/\/github\.com\/jacquesbach\/doppelkopf"/);
  assert.doesNotMatch(html, /<script/i);
  assert.match(staticContent("landing"), /<a href="\/regeln">/);
});

// --- nginx-Konfiguration: Abgleich mit dem Router (ohne nginx, nur Text) ------------------------------------------------------
const nginx = read("deploy/nginx.conf");

test("nginx kennt jede Seite des Routers", () => {
  for (const word of ["regeln", "impressum", "datenschutz", "neu", "beitreten", "tisch", "admin"]) {
    assert.ok(nginx.includes(word), `deploy/nginx.conf erwähnt /${word} nicht – Seite im Router, aber nicht in nginx?`);
  }
});

test("nginx: Adress-Muster für dynamische Seiten stimmen mit dem Router überein", () => {
  const line = nginx.split("\n").find((l) => l.includes("location ~ \"^/(neu|admin"));
  assert.ok(line, "Zeile für dynamische Seiten fehlt");
  const re = new RegExp(/"(\^[^"]+)"/.exec(line)[1]);
  for (const path of ["/neu", "/neu/", "/admin", "/beitreten", "/beitreten/AB12", "/beitreten/abcdefghijkl", "/tisch/XYZ9"]) {
    assert.ok(re.test(path), `${path} sollte die App-Hülle bekommen`);
    assert.notEqual(matchRoute(path).name, "notfound", `${path} kennt der Router`);
  }
  for (const path of ["/tisch", "/tisch/a", "/tisch/ABCDEFGHIJKLM", "/neu/x", "/admin/etwas", "/beitreten/AB-12"]) {
    assert.ok(!re.test(path), `${path} muss 404 liefern`);
    assert.equal(matchRoute(path).name === "notfound" || path === "/tisch", true, `${path} ist im Router ebenfalls unbekannt`);
  }
});

test("nginx: IP-Kürzung im Protokoll (Regeln aus der Konfiguration ausgewertet)", () => {
  const rules = [...nginx.matchAll(/^\s*"~(.+)"\s+(\S+);$/gm)].map((m) => ({ re: new RegExp(m[1].replace("(?P<", "(?<")), value: m[2] }));
  assert.equal(rules.length, 4);
  const anon = (ip) => {
    for (const { re, value } of rules) {
      const m = re.exec(ip);
      if (m) return value.replace("$ip", m.groups.ip);
    }
    return "0.0.0.0";
  };
  assert.equal(anon("203.0.113.77"), "203.0.113.0");
  assert.equal(anon("172.18.0.3"), "172.18.0.0");
  assert.equal(anon("2001:db8:abcd:1234:5678:9abc:def0:1234"), "2001:db8:abcd::");
  assert.equal(anon("2001:db8::1"), "2001:db8::");
  assert.equal(anon("fe80::1"), "fe80::");
  assert.equal(anon("::1"), "0.0.0.0");
  assert.equal(anon("::ffff:1.2.3.4"), "0.0.0.0");
  assert.doesNotMatch(nginx, /log_format anon[^;]*\$remote_addr[^_]/);   // nie die volle Adresse protokollieren
  assert.doesNotMatch(nginx, /log_format anon[^;]*\$http_referer/);
});
