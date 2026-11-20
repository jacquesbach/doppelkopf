// Freiwilliger Online-Status: eigene Socket-Verbindung, nur solange die Funktion eingeschaltet ist.
import {
  addFriend, applyPresence, cleanName, generateCode, loadFriends, parseCode, removeFriend, saveFriends,
} from "./friends.js";
import { siteSettings } from "./siteSettings.svelte.js";

class PresenceStore {
  enabled = $state(false);
  code = $state("");
  name = $state("");
  friends = $state([]);
  live = $state({}); // code -> { name } der gerade sichtbaren Freunde
  connected = $state(false);
  error = $state("");
  invites = $state([]); // { id, from, table, hasPassword }
  sent = $state({}); // code -> "sent" | "offline"
  dialogOpen = $state(false);
  table = $state(null); // { code, token }: der Tisch, an dem ich sitze (für Einladungen)

  #storage = null;
  #io = null;
  #origin = "";
  #socket = null;
  #seq = 0;

  init(storage, ioFactory, origin) {
    this.#storage = storage;
    this.#io = ioFactory;
    this.#origin = origin;
    const saved = loadFriends(storage);
    this.code = saved.code;
    this.name = saved.name;
    this.friends = saved.friends;
    this.enabled = saved.enabled;
    // Verbunden wird erst in sync(), nachdem die Einstellungen des Betreibers geladen sind (Funktion evtl. abgeschaltet).
  }

  /** Betreiber kann die Funktion abschalten: dann Verbindung trennen und Bedienelemente ausblenden. */
  get available() {
    return siteSettings.value.friendsEnabled;
  }

  #persist() {
    if (this.#storage) saveFriends(this.#storage, { enabled: this.enabled, code: this.code, name: this.name, friends: this.friends });
  }

  open() {
    this.dialogOpen = true;
  }
  close() {
    this.dialogOpen = false;
    this.error = "";
  }

  /** Einschalten: ausdrückliche Entscheidung der Person (Einwilligung). Erzeugt bei Bedarf einen neuen Code. */
  enable(rawName) {
    const name = cleanName(rawName);
    if (!name) {
      this.error = "Bitte wähle einen Anzeigenamen (er ist für deine Freunde sichtbar, solange du online bist).";
      return false;
    }
    this.error = "";
    this.name = name;
    if (!this.code) this.code = generateCode();
    this.enabled = true;
    this.#persist();
    this.#start();
    return true;
  }

  /** Ausschalten: sofort unsichtbar, Verbindung weg. Code und Liste bleiben im Browser (löschbar mit `forget`). */
  disable() {
    this.enabled = false;
    this.#stop(true);
    this.#persist();
  }

  /** Alles lokal löschen (Code, Name, Liste). */
  forget() {
    this.enabled = false;
    this.#stop(true);
    this.code = "";
    this.name = "";
    this.friends = [];
    this.live = {};
    this.#persist();
  }

  /** Neuen Code erzeugen (alte Einträge bei Freunden werden damit wirkungslos). */
  renewCode() {
    const wasOn = this.enabled;
    if (wasOn) this.#stop(true);
    this.code = generateCode();
    this.#persist();
    if (wasOn) this.#start();
  }

  rename(rawName) {
    const name = cleanName(rawName);
    if (!name) return false;
    this.name = name;
    this.#persist();
    if (this.enabled) {
      this.#stop(true);
      this.#start();
    }
    return true;
  }

  add(rawCode, rawName) {
    const result = addFriend(this.friends, this.code, rawCode, rawName);
    if (result.error) {
      this.error = result.error;
      return false;
    }
    this.error = "";
    this.friends = result.friends;
    this.#persist();
    this.#watch();
    return true;
  }

  remove(code) {
    this.friends = removeFriend(this.friends, code);
    const { [code]: _gone, ...rest } = this.live;
    this.live = rest;
    this.#persist();
    this.#watch();
  }

  invite(friendCode) {
    if (!this.#socket || !this.table || !parseCode(friendCode)) return;
    this.sent = { ...this.sent, [friendCode]: "pending" };
    this.#socket.emit("presence:invite", { to: friendCode, table: this.table.code, token: this.table.token });
  }

  dismissInvite(id) {
    this.invites = this.invites.filter((i) => i.id !== id);
  }

  #watch() {
    if (this.#socket && this.connected) this.#socket.emit("presence:watch", { codes: this.friends.map((f) => f.code) });
  }

  #start() {
    if (this.#socket || !this.#io || !this.available) return;
    const socket = this.#io(this.#origin, { transports: ["websocket", "polling"], reconnection: true });
    this.#socket = socket;
    socket.on("connect", () => {
      socket.emit("presence:hello", { code: this.code, name: this.name });
    });
    socket.on("presence:ready", () => {
      this.connected = true;
      this.error = "";
      this.#watch();
    });
    socket.on("disconnect", () => {
      this.connected = false;
      this.live = {};
    });
    socket.on("presence:state", (event) => (this.live = applyPresence(this.live, event)));
    socket.on("presence:update", (event) => {
      if (this.friends.some((f) => f.code === event?.code)) this.live = applyPresence(this.live, event);
    });
    socket.on("presence:invite", (event) => {
      const table = typeof event?.table === "string" ? event.table : "";
      if (!/^[A-Z0-9]{6}$/.test(table)) return;
      this.#seq += 1;
      this.invites = [
        ...this.invites.filter((i) => i.table !== table),
        { id: this.#seq, from: cleanName(event.from) || "Jemand", table, hasPassword: !!event.hasPassword },
      ].slice(-3);
    });
    socket.on("presence:invited", (event) => {
      this.sent = { ...this.sent, [event?.to]: event?.delivered ? "sent" : "offline" };
    });
    socket.on("presence:error", (event) => {
      this.error = typeof event?.message === "string" ? event.message : "Fehler beim Online-Status.";
    });
  }

  #stop(say) {
    const socket = this.#socket;
    this.#socket = null;
    this.connected = false;
    this.live = {};
    this.sent = {};
    if (!socket) return;
    if (say) socket.emit("presence:goodbye", {});
    socket.removeAllListeners?.();
    socket.disconnect();
  }

  /** Betreiber hat die Funktion abgeschaltet: unsichtbar werden, ohne die lokale Wahl zu überschreiben. */
  sync() {
    if (!this.available) this.#stop(true);
    else if (this.enabled && !this.#socket) this.#start();
  }
}

export const presence = new PresenceStore();
