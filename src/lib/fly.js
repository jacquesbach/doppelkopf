// Karten „fliegen“ zwischen Hand und Armuts-Fenster: ein Paar aus Senden/Empfangen (Svelte crossfade) für beide Komponenten.
import { crossfade } from "svelte/transition";
import { cubicOut } from "svelte/easing";

const reduced = () => !!globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export const [send, receive] = crossfade({
  duration: (distance) => (reduced() ? 0 : Math.min(520, 200 + Math.sqrt(distance) * 12)),
  easing: cubicOut,
  fallback: () => ({ duration: 0 }), // Karte ohne Gegenstück (z. B. normal ausgespielt): kein Effekt
});
