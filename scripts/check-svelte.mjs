// Schneller Syntax-Check für .svelte-Dateien OHNE Svelte-Compiler (z. B. wenn npm-Pakete fehlen).
// Prüft: <script>-Blöcke (JS-Syntax), Block-Balance ({#if}/{#each}/{#key}/{#snippet}), Ausdrücke in {…}
// und die Tag-Balance im Markup. Ersetzt NICHT `vite build`, fängt aber Tippfehler früh ab.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { transformSync } from "esbuild";

const VOID = new Set(["br", "hr", "img", "input", "meta", "link", "path", "circle", "rect", "line", "polygon", "polyline", "ellipse", "use", "stop"]);
const errors = [];
const fail = (file, msg) => errors.push(`${file}: ${msg}`);

function parseJs(file, code, what) {
  try {
    transformSync(code, { loader: "js", format: "esm" });
  } catch (e) {
    fail(file, `${what}: ${String(e.errors?.[0]?.text ?? e.message)} – «${code.slice(0, 70).replace(/\s+/g, " ")}»`);
  }
}

function walk(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

/** Liest ab src[i] == "{" bis zur passenden "}" (Strings und Template-Literale mit ${…} werden beachtet). */
function matchBrace(src, i) {
  let j = i + 1;
  while (j < src.length) {
    const c = src[j];
    if (c === "}") return j;
    if (c === "{") j = matchBrace(src, j);
    else if (c === '"' || c === "'") {
      for (j++; j < src.length && src[j] !== c; j++) if (src[j] === "\\") j++;
    } else if (c === "`") {
      for (j++; j < src.length && src[j] !== "`"; j++) {
        if (src[j] === "\\") j++;
        else if (src[j] === "$" && src[j + 1] === "{") j = matchBrace(src, j + 1);
      }
    }
    if (j === -1) return -1;
    j++;
  }
  return -1;
}

/** Zerlegt Markup in Text-/Klammer-Segmente. */
function braces(src, file) {
  const out = [];
  let i = 0;
  let text = "";
  while (i < src.length) {
    if (src[i] !== "{") { text += src[i++]; continue; }
    const j = matchBrace(src, i);
    if (j < 0) { fail(file, `Nicht geschlossene { … } (Zeile ≈ ${src.slice(0, i).split("\n").length})`); break; }
    out.push({ text });
    out.push({ brace: src.slice(i + 1, j) });
    text = "";
    i = j + 1;
  }
  out.push({ text });
  return out;
}

for (const file of walk("src")) {
  if (file.endsWith(".js")) { parseJs(file, readFileSync(file, "utf8").replace(/\$(state|derived|effect|props|bindable)/g, "__$1"), "JS"); continue; }
  if (!file.endsWith(".svelte")) continue;
  let src = readFileSync(file, "utf8");
  src = src.replace(/<style[\s\S]*?<\/style>/g, "");
  src = src.replace(/<script[^>]*>([\s\S]*?)<\/script>/g, (_, code) => {
    parseJs(file, code.replace(/\$(state|derived|effect|props|bindable)/g, "__$1"), "script");
    return "";
  });
  const segments = braces(src, file);
  const blocks = [];
  let markup = "";
  for (const seg of segments) {
    if (seg.text !== undefined) { markup += seg.text; continue; }
    markup += "{}";
    const b = seg.brace.trim();
    let m;
    if ((m = /^#(if|key)\s+([\s\S]+)$/.exec(b))) { blocks.push(m[1]); parseJs(file, `(${m[2]})`, `{#${m[1]}}`); }
    else if ((m = /^#each\s+([\s\S]+?)\s+as\s+([\s\S]+)$/.exec(b))) {
      blocks.push("each"); parseJs(file, `(${m[1]})`, "{#each}");
      const key = /\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$/.exec(m[2]);
      if (key) parseJs(file, `(${key[1]})`, "{#each} key");
    }
    else if (/^#snippet\s/.test(b)) blocks.push("snippet");
    else if ((m = /^:else if\s+([\s\S]+)$/.exec(b))) { if (blocks.at(-1) !== "if") fail(file, "{:else if} außerhalb von {#if}"); parseJs(file, `(${m[1]})`, "{:else if}"); }
    else if (b === ":else") { if (!["if", "each"].includes(blocks.at(-1))) fail(file, "{:else} außerhalb von if/each"); }
    else if ((m = /^\/(if|each|key|snippet)$/.exec(b))) { if (blocks.pop() !== m[1]) fail(file, `{/${m[1]}} ohne passenden Anfang`); }
    else if ((m = /^@render\s+([\s\S]+)$/.exec(b))) parseJs(file, `(${m[1]})`, "{@render}");
    else if ((m = /^@html\s+([\s\S]+)$/.exec(b))) parseJs(file, `(${m[1]})`, "{@html}");
    else if ((m = /^@const\s+([\s\S]+)$/.exec(b))) parseJs(file, `const ${m[1]}`, "{@const}");
    else if (/^[#:\/@]/.test(b)) fail(file, `Unbekannter Block {${b.slice(0, 30)}}`);
    else {
      // Attribut-/Text-Ausdruck: "...x" (Spread) und {x} (Kurzform) zulassen
      const expr = b.replace(/^\.\.\./, "");
      parseJs(file, `(${expr})`, `{${b.slice(0, 40)}}`);
    }
  }
  if (blocks.length) fail(file, `Nicht geschlossene Blöcke: ${blocks.join(", ")}`);

  // Tag-Balance
  markup = markup.replace(/<!--[\s\S]*?-->/g, "");
  const stack = [];
  for (const m of markup.matchAll(/<(\/?)([A-Za-z][\w:.-]*)((?:"[^"]*"|'[^']*'|[^'">])*?)(\/?)>/g)) {
    const [, closing, name, , selfClosing] = m;
    if (selfClosing || VOID.has(name)) continue; // <path></path> und <input> sind für die Balance egal
    if (!closing) stack.push(name);
    else if (stack.pop() !== name) { fail(file, `</${name}> passt nicht zum geöffneten Tag (Zeile ≈ ${markup.slice(0, m.index).split("\n").length})`); break; }
  }
  if (stack.length) fail(file, `Nicht geschlossene Tags: ${stack.join(", ")}`);
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log("Svelte-Syntaxcheck: OK");
