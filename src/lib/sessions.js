// Merkt sich pro Raum das Sitzungs-Token (localStorage), damit ein Neuladen den Platz behält.
const SESSIONS_KEY = "doko.sessions.v1";
const NAME_KEY = "doko.name.v1";

export function createSessions(storage) {
  function read() {
    try {
      const data = JSON.parse(storage.getItem(SESSIONS_KEY) || "{}");
      return data && typeof data === "object" ? data : {};
    } catch {
      return {};
    }
  }
  function write(data) {
    try {
      storage.setItem(SESSIONS_KEY, JSON.stringify(data));
    } catch {
      /* Speicher voll oder gesperrt: dann eben ohne Wiedererkennung */
    }
  }
  return {
    get: (code) => read()[String(code).toUpperCase()] ?? null,
    set(code, session) {
      const data = read();
      data[String(code).toUpperCase()] = session;
      write(data);
    },
    remove(code) {
      const data = read();
      delete data[String(code).toUpperCase()];
      write(data);
    },
    lastName() {
      try {
        return storage.getItem(NAME_KEY) || "";
      } catch {
        return "";
      }
    },
    rememberName(name) {
      try {
        storage.setItem(NAME_KEY, name);
      } catch {
        /* ignorieren */
      }
    },
  };
}
