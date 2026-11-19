// Lokal weiterlaufender Countdown: Der Server meldet nur alle paar Sekunden, wie viel Zeit bleibt (`remaining`, gültig
// zum Empfangszeitpunkt `at`). Im Komponenten-Kontext aufrufen (benötigt $effect für die Uhr).
import { countdownLeft } from "./view.js";

/** @param {() => ({ remaining: number, at: number } | null)} source */
export function useCountdown(source) {
  let now = $state(Date.now());
  $effect(() => {
    const timer = setInterval(() => (now = Date.now()), 250);
    return () => clearInterval(timer);
  });
  return {
    get left() {
      const s = source();
      return s ? countdownLeft(s.remaining, s.at, now) : 0;
    },
  };
}
