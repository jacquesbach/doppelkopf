// Gemeinsame Dienste der App (eine Instanz pro Seitenaufruf).
import { io } from "socket.io-client";
import { createApi, socketOrigin } from "./api.js";
import { getClientId } from "./clientId.js";
import { createLabSeats } from "./lab.js";
import { createSessions } from "./sessions.js";
import { tableTheme } from "./theme.svelte.js";
import { presence } from "./presence.svelte.js";

const baseUrl = import.meta.env?.VITE_API_BASE_URL || "/api";

export const api = createApi({ baseUrl, clientId: () => getClientId(window.localStorage) });
export const sessions = createSessions(window.localStorage);
export const labSeats = createLabSeats(window.localStorage);
export const realtime = {
  ioFactory: io,
  origin: socketOrigin(baseUrl, window.location),
};

tableTheme.init(window.localStorage); // Hell/Dunkel am Tisch: gespeicherte Wahl des Besuchers
presence.init(window.localStorage, io, realtime.origin); // Online-Status nur, wenn die Person ihn selbst eingeschaltet hat
