#!/usr/bin/env bash
# Prüft eine laufende Installation (nginx + Frontend-Build + Backend) von aussen mit curl.
#   bash scripts/smoke-test.sh http://127.0.0.1:8080
# Läuft in der CI (build-and-test.yml) und nach jedem Deploy (deploy.yml, per ssh auf dem Server).
set -u

BASE="${1:-http://127.0.0.1:8080}"
BASE="${BASE%/}"
fail=0

ok()  { printf '  ok    %s\n' "$1"; }
bad() { printf '::error::%s\n' "$1"; fail=1; }

# fetch <pfad> [weitere curl-Argumente]: schreibt Kopf in /tmp/smoke.head, Inhalt in /tmp/smoke.body, gibt den Statuscode aus
fetch() {
  local path="$1"; shift
  curl -s --max-time 10 -D /tmp/smoke.head -o /tmp/smoke.body -w '%{http_code}' "$@" "$BASE$path" || echo 000
}
header() { grep -i "^$1:" /tmp/smoke.head | tr -d '\r' | head -1; }

expect_status() { # pfad erwarteter-status
  local code; code=$(fetch "$1")
  if [ "$code" = "$2" ]; then ok "$1 -> $code"; else bad "$1 liefert $code statt $2"; fi
}

expect_in_body() { # beschreibung muster
  if grep -qE "$2" /tmp/smoke.body; then ok "$1"; else bad "$1 (Muster fehlt: $2)"; fi
}

echo "Smoke-Test gegen $BASE"

# --- Seiten: Status, Titel, canonical ----------------------------------------------------------------------------------------
for entry in "/|Doppelkopf online spielen|/\"" "/regeln|Doppelkopf-Regeln einfach erklärt|/regeln\"" "/regeln/|Doppelkopf-Regeln einfach erklärt|/regeln\""; do
  path="${entry%%|*}"; rest="${entry#*|}"; title="${rest%%|*}"; canon="${rest#*|}"
  code=$(fetch "$path")
  if [ "$code" != 200 ]; then bad "$path liefert $code statt 200"; continue; fi
  expect_in_body "$path: Titel '$title'" "<title>[^<]*$title"
  expect_in_body "$path: canonical endet auf $canon" "rel=\"canonical\" href=\"https?://[^\"]*$canon"
  expect_in_body "$path: robots index" 'name="robots" content="index'
  expect_in_body "$path: Klartext-Inhalt (noscript)" '<noscript id="static-content">'
done

for path in /impressum /datenschutz; do
  code=$(fetch "$path")
  if [ "$code" != 200 ]; then bad "$path liefert $code statt 200"; continue; fi
  expect_in_body "$path: noindex" 'name="robots" content="noindex'
  if grep -q 'rel="canonical"' /tmp/smoke.body; then bad "$path: darf keine canonical-Angabe haben (noindex)"; else ok "$path: keine canonical"; fi
done

# --- Dynamische Seiten: erreichbar, aber nie im Index ----------------------------------------------------------------------
for path in /neu /beitreten /beitreten/AB12 /tisch/AB12 /admin; do
  code=$(fetch "$path")
  if [ "$code" != 200 ]; then bad "$path liefert $code statt 200"; continue; fi
  if header x-robots-tag | grep -qi noindex; then ok "$path -> 200, X-Robots-Tag noindex"; else bad "$path: X-Robots-Tag noindex fehlt"; fi
done

# --- Fehlerseiten: echter 404-Status statt "Soft 404" ----------------------------------------------------------------------
code=$(fetch /gibt-es-nicht)
if [ "$code" = 404 ]; then ok "/gibt-es-nicht -> 404"; else bad "/gibt-es-nicht liefert $code statt 404"; fi
expect_in_body "404-Seite enthält die App-Hülle" 'id="app"'
for path in /index.html /regeln/index.html /tisch/a /beitreten/ABCDEFGHIJKLM; do
  code=$(fetch "$path")
  if [ "$code" = 404 ]; then ok "$path -> 404"; else bad "$path liefert $code statt 404"; fi
done

# --- robots.txt und sitemap.xml -----------------------------------------------------------------------------------------------
code=$(fetch /robots.txt)
[ "$code" = 200 ] && ok "/robots.txt -> 200" || bad "/robots.txt liefert $code"
expect_in_body "robots.txt nennt die Sitemap" '^Sitemap: https?://'
expect_in_body "robots.txt sperrt /api/" '^Disallow: /api/'
code=$(fetch /sitemap.xml)
[ "$code" = 200 ] && ok "/sitemap.xml -> 200" || bad "/sitemap.xml liefert $code"
expect_in_body "sitemap.xml enthält /regeln" '<loc>https?://[^<]*/regeln</loc>'
if grep -q '/tisch\|/admin\|/impressum' /tmp/smoke.body; then bad "sitemap.xml enthält Seiten, die nicht in den Index sollen"; else ok "sitemap.xml enthält nur indexierbare Seiten"; fi

# --- Dateien: Cache und Kompression ---------------------------------------------------------------------------------------------
fetch / > /dev/null
asset=$(grep -oE '/assets/[A-Za-z0-9._-]+\.js' /tmp/smoke.body | head -1)
if [ -z "$asset" ]; then
  bad "kein JavaScript-Bundle in der Startseite gefunden"
else
  code=$(fetch "$asset" -H 'Accept-Encoding: gzip')
  [ "$code" = 200 ] && ok "$asset -> 200" || bad "$asset liefert $code"
  header cache-control | grep -qi immutable && ok "Bundle: Cache-Control immutable" || bad "Bundle: Cache-Control immutable fehlt"
  header content-encoding | grep -qi gzip && ok "Bundle: gzip aktiv" || bad "Bundle: gzip fehlt"
fi
for path in /favicon.svg /favicon.ico /apple-touch-icon.png /og-image.png /manifest.webmanifest; do
  expect_status "$path" 200
done

# --- Backend hinter nginx -------------------------------------------------------------------------------------------------------
expect_status /api/health 200

if [ "$fail" = 0 ]; then echo "Smoke-Test bestanden."; else echo "Smoke-Test FEHLGESCHLAGEN."; fi
exit "$fail"
