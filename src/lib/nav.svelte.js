// Seitenwechsel ohne Neuladen. `nav.route` ist reaktiv; `link` ist eine Svelte-Action für interne Links.
import { matchRoute } from "./router.js";

export const nav = $state({ route: matchRoute(window.location.pathname) });

window.addEventListener("popstate", () => {
  const next = matchRoute(window.location.pathname);
  if (JSON.stringify(next) !== JSON.stringify(nav.route)) nav.route = next;
});

export function navigate(path, { replace = false } = {}) {
  const url = new URL(path, window.location.origin);
  const target = url.pathname + url.search + url.hash;
  if (replace) window.history.replaceState({}, "", target);
  else window.history.pushState({}, "", target);
  nav.route = matchRoute(url.pathname);
  window.scrollTo(0, 0);
}

/** use:link – interne Links per History API öffnen (Strg/Cmd-Klick und neue Tabs bleiben normal). */
export function link(node) {
  function onClick(event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const href = node.getAttribute("href");
    if (!href || !href.startsWith("/")) return;
    event.preventDefault();
    navigate(href);
  }
  node.addEventListener("click", onClick);
  return { destroy: () => node.removeEventListener("click", onClick) };
}
