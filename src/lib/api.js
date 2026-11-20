// HTTP-Client für das Backend (siehe docs/API.md). Fetch ist injizierbar (Tests).
export class ApiError extends Error {
  constructor(message, { status = 0, code = null, version = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.version = version;
  }
  get isVersionConflict() {
    return this.code === "version_conflict";
  }
}

export function newActionId() {
  const c = globalThis.crypto;
  if (c?.randomUUID) return c.randomUUID();
  return `a${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

export function socketOrigin(baseUrl, location) {
  // "/api" (gleicher Ursprung) → Ursprung der Seite; "http://host:8181/api" → "http://host:8181"
  if (/^https?:\/\//.test(baseUrl)) return baseUrl.replace(/\/api\/?$/, "");
  return location?.origin ?? "";
}

export function createApi({ baseUrl = "/api", fetchImpl, clientId = null } = {}) {
  const doFetch = fetchImpl ?? ((...a) => globalThis.fetch(...a));

  async function request(method, path, { token, body, bearer, withClient } = {}) {
    const headers = {};
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    if (withClient && clientId) headers["X-Client-Id"] = typeof clientId === "function" ? clientId() : clientId;
    if (token) headers["X-Session-Token"] = token;
    // Ältere Raum-Routen lesen das Token aus dem Body, die Spiel-Routen aus dem Header: beides senden.
    if (token && method === "POST") body = { ...(body ?? {}), token };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let res;
    try {
      res = await doFetch(`${baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError("Keine Verbindung zum Server.", { status: 0, code: "network" });
    }
    let data = null;
    try {
      data = await res.json();
    } catch {
      /* leere Antwort */
    }
    if (!res.ok) {
      throw new ApiError(data?.error ?? data?.message ?? `Fehler ${res.status}`, {
        status: res.status,
        code: data?.code ?? null,
        version: data?.version ?? null,
      });
    }
    return data;
  }

  const admin = (bearer) => ({ bearer });
  const room = (code) => `/rooms/${encodeURIComponent(code)}`;
  return {
    ruleSchema: () => request("GET", "/rule-schema"),
    createRoom: ({ name, password, settings, isPublic = false }) =>
      request("POST", "/rooms", { body: { name, password: password || undefined, settings, public: isPublic } }),
    publicRooms: () => request("GET", "/rooms/public"),
    setVisibility: (code, token, isPublic) =>
      request("POST", `${room(code)}/visibility`, { token, body: { public: isPublic } }),
    joinRoom: (code, { name, role = "player", password }) =>
      request("POST", `${room(code)}/join`, { body: { name, role, password: password || undefined } }),
    getRoom: (code, token) => request("GET", room(code), { token }),
    setReady: (code, token, ready) => request("POST", `${room(code)}/ready`, { token, body: { ready } }),
    addBot: (code, token) => request("POST", `${room(code)}/bots`, { token, body: {} }),
    leave: (code, token) => request("POST", `${room(code)}/leave`, { token, body: {} }),
    saveSettings: (code, token, settings) =>
      request("POST", `${room(code)}/settings`, { token, body: { settings } }),
    start: (code, token) => request("POST", `${room(code)}/start`, { token, body: {} }),
    getGame: (code, token) => request("GET", `${room(code)}/game`, { token }),
    action: (code, token, action, expectedVersion) =>
      request("POST", `${room(code)}/action`, {
        token,
        body: { ...action, expectedVersion, actionId: newActionId() },
      }),
    next: (code, token) => request("POST", `${room(code)}/next`, { token, body: {} }),
    history: (code, token) => request("GET", `${room(code)}/history`, { token }),
    continueGame: (code, token) => request("POST", `${room(code)}/continue`, { token, body: {} }),
    setTakeover: (code, token, seconds) => request("POST", `${room(code)}/takeover`, { token, body: { seconds } }),
    stay: (code, token, remember) =>
      request("POST", `${room(code)}/stay`, { token, body: remember === undefined ? {} : { remember } }),
    away: (code, token) => request("POST", `${room(code)}/away`, { token, body: {} }),
    back: (code, token) => request("POST", `${room(code)}/back`, { token, body: {} }),
    rejoin: (code, { name, password }) =>
      request("POST", `${room(code)}/rejoin`, { body: { name, password: password || undefined } }),
    chatHistory: (code, token) => request("GET", `${room(code)}/chat`, { token }),
    chatPost: (code, token, text) => request("POST", `${room(code)}/chat`, { token, body: { text } }),

    // Vorschläge, Daumen, Captcha, Sprüche (öffentlich)
    captcha: () => request("GET", "/captcha"),
    phrases: () => request("GET", "/phrases"),
    suggestions: () => request("GET", "/suggestions", { withClient: true }),
    submitSuggestion: (fields) => request("POST", "/suggestions", { body: fields, withClient: true }),
    voteSuggestion: (id) => request("POST", `/suggestions/${id}/vote`, { withClient: true }),

    // Design-Einstellungen und Banner (öffentlich lesbar)
    siteSettings: () => request("GET", "/site-settings"),

    // Betreiber-Backend (Token aus adminLogin)
    adminStatus: () => request("GET", "/admin/status"),
    adminLogin: (password) => request("POST", "/admin/login", { body: { password } }),
    adminTables: (t) => request("GET", "/admin/tables", admin(t)),
    adminLive: (t) => request("GET", "/admin/live", admin(t)),
    adminLiveMessage: (t, code, message) =>
      request("POST", `/admin/live/${encodeURIComponent(code)}/message`, { ...admin(t), body: { message } }),
    adminLiveClose: (t, code, message) =>
      request("POST", `/admin/live/${encodeURIComponent(code)}/close`, { ...admin(t), body: { message } }),
    adminLiveSpectate: (t, code) => request("POST", `/admin/live/${encodeURIComponent(code)}/spectate`, { ...admin(t), body: {} }),
    adminInsights: (t) => request("GET", "/admin/insights", admin(t)),
    adminSystem: (t) => request("GET", "/admin/system", admin(t)),
    adminErrors: (t) => request("GET", "/admin/errors", admin(t)),
    adminDeleteError: (t, id) => request("DELETE", `/admin/errors/${id}`, admin(t)),
    adminClearErrors: (t) => request("DELETE", "/admin/errors", admin(t)),
    adminSiteSettings: (t) => request("GET", "/admin/site-settings", admin(t)),
    adminSaveSiteSettings: (t, settings) => request("PUT", "/admin/site-settings", { ...admin(t), body: settings }),
    adminResetSiteSettings: (t) => request("POST", "/admin/site-settings/reset", { ...admin(t), body: {} }),
    adminStats: (t) => request("GET", "/admin/stats", admin(t)),
    adminPhrases: (t) => request("GET", "/admin/phrases", admin(t)),
    adminAddPhrase: (t, text) => request("POST", "/admin/phrases", { ...admin(t), body: { text } }),
    adminEditPhrase: (t, id, text) => request("PUT", `/admin/phrases/${id}`, { ...admin(t), body: { text } }),
    adminDeletePhrase: (t, id) => request("DELETE", `/admin/phrases/${id}`, admin(t)),
    adminMovePhrase: (t, id, direction) => request("POST", `/admin/phrases/${id}/move`, { ...admin(t), body: { direction } }),
    adminSuggestions: (t) => request("GET", "/admin/suggestions", admin(t)),
    adminSuggestionStatus: (t, id, status) => request("POST", `/admin/suggestions/${id}/status`, { ...admin(t), body: { status } }),
    adminEditSuggestion: (t, id, title, description) =>
      request("PUT", `/admin/suggestions/${id}`, { ...admin(t), body: { title, description } }),
    adminDeleteSuggestion: (t, id) => request("DELETE", `/admin/suggestions/${id}`, admin(t)),

    // Test-Tisch (Betreiber)
    adminLabPresets: (t) => request("GET", "/admin/lab/presets", admin(t)),
    adminLabTables: (t) => request("GET", "/admin/lab/tables", admin(t)),
    adminLabCreate: (t, scenario) => request("POST", "/admin/lab/tables", { ...admin(t), body: { scenario } }),
    adminLabReset: (t, code, scenario) =>
      request("POST", `/admin/lab/tables/${encodeURIComponent(code)}/reset`, { ...admin(t), body: scenario ? { scenario } : {} }),
    adminLabOpen: (t, code) => request("POST", `/admin/lab/tables/${encodeURIComponent(code)}/open`, { ...admin(t), body: {} }),
    adminLabDelete: (t, code) => request("DELETE", `/admin/lab/tables/${encodeURIComponent(code)}`, admin(t)),
  };
}
