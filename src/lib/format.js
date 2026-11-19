// Anzeigehilfen für das Betreiber-Backend (Dauer, Zeitpunkte, Zahlen).
export function formatDuration(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  if (s < 60) return `${s} Sek.`;
  const minutes = Math.floor(s / 60);
  if (minutes < 60) return `${minutes} Min.`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return minutes % 60 ? `${hours} Std. ${minutes % 60} Min.` : `${hours} Std.`;
  const days = Math.floor(hours / 24);
  return hours % 24 ? `${days} T. ${hours % 24} Std.` : `${days} T.`;
}

export function formatMinutes(minutes) {
  const m = Number(minutes) || 0;
  return m >= 100 ? String(Math.round(m)) : (Math.round(m * 10) / 10).toString().replace(".", ",");
}

export function formatNumber(value) {
  return new Intl.NumberFormat("de-DE").format(Number(value) || 0);
}

export function formatDateTime(epochSeconds) {
  if (!epochSeconds) return "–";
  return new Date(epochSeconds * 1000).toLocaleString("de-DE", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

export function percent(part, whole) {
  return whole ? `${Math.round((part / whole) * 100)} %` : "–";
}
