// Gemeinsame Dienste der App (eine Instanz pro Seitenaufruf).
import { io } from "socket.io-client";
import { createApi, socketOrigin } from "./api.js";
import { getClientId } from "./clientId.js";
import { createLabSeats } from "./lab.js";
import { createSessions } from "./sessions.js";

const baseUrl = import.meta.env?.VITE_API_BASE_URL || "/api";

export const api = createApi({ baseUrl, clientId: () => getClientId(window.localStorage) });
export const sessions = createSessions(window.localStorage);
export const labSeats = createLabSeats(window.localStorage);
export const realtime = {
  ioFactory: io,
  origin: socketOrigin(baseUrl, window.location),
};
