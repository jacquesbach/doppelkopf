<script>
  import PageShell from "../components/ui/PageShell.svelte";

  let { page = "impressum" } = $props();
</script>

<PageShell narrow>
  {#if page === "impressum"}
    <span class="nx-badge nx-bg-yellow">RECHTLICHES</span>
    <h1 class="nx-title">Impressum</h1>
    <div class="nx-box nx-prose">
      <p>
        <strong>Platzhalter:</strong> Hier müssen die Angaben des Betreibers nach § 5 DDG (Name, Anschrift, E-Mail)
        stehen, sobald die App öffentlich betrieben wird. Die Datei liegt unter
        <code>src/pages/Legal.svelte</code>.
      </p>
    </div>
  {:else}
    <span class="nx-badge nx-bg-yellow">RECHTLICHES</span>
    <h1 class="nx-title">Datenschutz</h1>
    <div class="nx-box nx-prose">
      <p>
        <strong>Platzhalter:</strong> Die endgültige Datenschutzerklärung hängt vom Betrieb ab (Hosting, Protokolle).
        Technisch gespeichert werden: Spielername, Tisch-Code, ein zufälliges Sitzungs-Token (im Browser per
        <code>localStorage</code> und als Hash in der Datenbank), der Spielstand und der Tisch-Chat im Arbeitsspeicher.
        Es gibt keine Werbung, kein Tracking und keine externen Schriftarten oder Skripte.
      </p>
      <p>
        <strong>Verbesserungsvorschläge:</strong> Titel und Beschreibung eines Vorschlags werden gespeichert und sind für
        alle sichtbar – bitte keine persönlichen Daten eintragen. Damit jeder Vorschlag nur einen Daumen je Person bekommt,
        legt dein Browser eine zufällige Kennung an (<code>localStorage</code>); in der Datenbank steht davon nur ein Hash.
        Zum Schutz vor Missbrauch (Begrenzung der Anfragen je Stunde) verarbeitet der Server kurzzeitig deine IP-Adresse
        im Arbeitsspeicher; sie wird nicht dauerhaft gespeichert.
      </p>
      <p>
        <strong>Nutzungsstatistik:</strong> Für jeden Tisch werden nur Zeitpunkte, Zahl der Menschen und Bots sowie Zahl der
        Spiele gezählt – ohne Namen, ohne Spielinhalte, ohne Chat.
      </p>
    </div>
  {/if}
</PageShell>
