// Minimaler Pfad-Router ohne Bibliothek (History API).
export function matchRoute(pathname) {
  const path = (pathname || "/").replace(/\/+$/, "") || "/";
  if (path === "/") return { name: "landing" };
  if (path === "/neu") return { name: "create" };
  if (path === "/beitreten") return { name: "join", code: "" };
  let m = /^\/beitreten\/([A-Za-z0-9]{3,12})$/.exec(path);
  if (m) return { name: "join", code: m[1].toUpperCase() };
  m = /^\/tisch\/([A-Za-z0-9]{3,12})$/.exec(path);
  if (m) return { name: "table", code: m[1].toUpperCase() };
  if (path === "/admin") return { name: "admin" };
  if (path === "/regeln") return { name: "rules" };
  if (path === "/impressum") return { name: "legal", page: "impressum" };
  if (path === "/datenschutz") return { name: "legal", page: "datenschutz" };
  return { name: "notfound" };
}

export function buildPath(name, params = {}) {
  switch (name) {
    case "landing": return "/";
    case "create": return "/neu";
    case "join": return params.code ? `/beitreten/${params.code}` : "/beitreten";
    case "table": return `/tisch/${params.code}`;
    case "legal": return `/${params.page}`;
    case "rules": return "/regeln";
    case "admin": return "/admin";
    default: return "/";
  }
}

export function inviteLink(origin, code) {
  return `${origin}${buildPath("join", { code })}`;
}
