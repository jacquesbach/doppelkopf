// Echtzeit-Verbindung (Socket.IO). `ioFactory` ist injizierbar, damit die Logik ohne Netzwerk testbar bleibt.
export function createRoomSocket({ ioFactory, origin, code, token, handlers = {} }) {
  const socket = ioFactory(origin, { transports: ["websocket", "polling"], reconnection: true });
  const watch = () => socket.emit("room:watch", { code, token });

  socket.on("connect", () => {
    watch(); // nach jedem (Wieder-)Verbinden erneut anmelden
    handlers.onStatus?.("online");
  });
  socket.on("disconnect", () => handlers.onStatus?.("offline"));
  socket.on("connect_error", () => handlers.onStatus?.("offline"));
  socket.on("room:state", (room) => handlers.onRoom?.(room));
  socket.on("game:state", (view) => handlers.onGame?.(view));
  socket.on("chat:message", (message) => handlers.onChat?.(message));
  socket.on("room:error", (error) => handlers.onError?.(error));

  return {
    close() {
      socket.removeAllListeners?.();
      socket.disconnect();
    },
  };
}
