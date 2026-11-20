<script>
  import { onMount } from "svelte";
  import PageShell from "../components/ui/PageShell.svelte";
  import { link } from "../lib/nav.svelte.js";
  import { addressLines, loadLegal, mailHref } from "../lib/legal.js";
  import { DDV_URL, GITHUB_URL, SITE_NAME } from "../lib/site.js";

  let { page = "impressum" } = $props();

  // Betreiberangaben kommen zur Laufzeit aus /legal/legal.json (siehe src/lib/legal.js und docs/DEPLOYMENT.md).
  let legal = $state(null);
  onMount(async () => {
    legal = await loadLegal();
  });

  const mail = $derived(legal ? mailHref(legal.email) : null);
  const PRIVACY_DATE = "20. November 2026";   // Datum der letzten inhaltlichen Änderung der Texte unten
</script>

<PageShell narrow>
  <span class="nx-badge nx-bg-yellow">RECHTLICHES</span>
  <h1 class="nx-title">{page === "datenschutz" ? "Datenschutzerklärung" : "Impressum"}</h1>

  {#if !legal}
    <p class="nx-muted" aria-live="polite">Lade Angaben …</p>
  {:else}
    {#if legal.demo}
      <div class="nx-error" role="note">
        <strong>TESTDATEN:</strong> Für diese Installation sind noch keine Betreiberangaben hinterlegt. Die Angaben unten sind
        erfunden und dürfen nicht für den öffentlichen Betrieb verwendet werden.
      </div>
    {/if}

    {#if page === "impressum"}
      <div class="nx-box nx-prose legal">
        <p class="nx-muted">Angaben gemäß § 5 Digitale-Dienste-Gesetz (DDG)</p>

        <h2 class="nx-h2">Anbieter</h2>
        <address>
          {#each addressLines(legal) as line}{line}<br />{/each}
        </address>

        <h2 class="nx-h2">Kontakt</h2>
        <p>
          E-Mail: {#if mail}<a href={mail}>{legal.email}</a>{:else}{legal.email}{/if}
          {#if legal.phone}<br />Telefon: {legal.phone}{/if}
        </p>

        {#if legal.vatId}
          <h2 class="nx-h2">Umsatzsteuer-Identifikationsnummer</h2>
          <p>{legal.vatId}</p>
        {/if}

        <h2 class="nx-h2">Verantwortlich für den Inhalt</h2>
        <p>Verantwortlich im Sinne von § 18 Abs. 2 MStV: {legal.name}, Anschrift wie oben.</p>

        <h2 class="nx-h2">Haftung für Inhalte</h2>
        <p>
          Die Inhalte dieser Seite werden mit Sorgfalt erstellt. Für Richtigkeit, Vollständigkeit und Aktualität, auch der
          Zusammenfassung der Spielregeln, übernehmen wir keine Gewähr.
        </p>
        <p>
          Besucher können Spielnamen, Chat-Nachrichten und Verbesserungsvorschläge eingeben. Für diese Beiträge sind die jeweiligen
          Verfasser verantwortlich. Hinweise auf rechtswidrige Inhalte schickst du bitte mit genauer Angabe der Fundstelle an die oben
          genannte E-Mail-Adresse (das gilt auch für Meldungen nach Art. 16 des Digital Services Act). Wir prüfen sie und entfernen
          rechtswidrige Inhalte unverzüglich.
        </p>

        <h2 class="nx-h2">Haftung für Links</h2>
        <p>
          Diese Seite verlinkt auf externe Seiten, zum Beispiel auf
          <a href={DDV_URL} target="_blank" rel="noopener noreferrer">den Deutschen Doppelkopf-Verband</a> und auf
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">GitHub</a>. Auf deren Inhalte haben wir keinen Einfluss
          und übernehmen dafür keine Verantwortung. Zum Zeitpunkt der Verlinkung waren keine Rechtsverstöße erkennbar.
        </p>

        <h2 class="nx-h2">Urheberrecht und Quellcode</h2>
        <p>
          Texte, Grafiken und Programmcode dieser Seite sind urheberrechtlich geschützt, soweit nichts anderes angegeben ist. Der
          Quellcode ist öffentlich auf <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">GitHub</a> einsehbar und
          steht unter der dort genannten Lizenz. Die Spielkarten sind selbst gezeichnete Vektorgrafiken.
        </p>

        <h2 class="nx-h2">Unabhängigkeit</h2>
        <p>
          {SITE_NAME} ist ein unabhängiges Projekt und steht in keiner Verbindung zum Deutschen Doppelkopf-Verband e. V. (DDV).
          Die DDV-Turnierspielregeln dienen als Regelgrundlage.
        </p>

        <p class="nx-muted">
          Weitere Informationen findest du in der <a href="/datenschutz" use:link>Datenschutzerklärung</a>.
        </p>
      </div>
    {:else}
      <div class="nx-box nx-prose legal">
        <p class="nx-muted">Stand: {PRIVACY_DATE}</p>
        <p>
          Hier erfährst du, welche personenbezogenen Daten beim Besuch von {SITE_NAME} und beim Spielen verarbeitet werden und
          welche Rechte du hast.
        </p>

        <h2 class="nx-h2">Das Wichtigste in Kürze</h2>
        <ul>
          <li>Es gibt kein Benutzerkonto. Zum Spielen genügt ein frei gewählter Spielname.</li>
          <li>Es werden keine Cookies gesetzt und kein Tracking oder Webanalyse eingesetzt. Es gibt keine Werbung.</li>
          <li>Schriftarten, Skripte und Grafiken kommen von unserem eigenen Server. Es werden keine Drittdienste eingebunden.</li>
          <li>Tische ohne Aktivität werden nach 12 Stunden samt Spielstand und Chat automatisch gelöscht.</li>
          <li>
            „Wer ist online“ ist freiwillig und standardmäßig aus. Niemand muss zeigen, dass er online ist. Auch das geht ohne
            Konto (Abschnitt 6).
          </li>
        </ul>

        <h2 class="nx-h2">1. Verantwortlicher</h2>
        <p>
          Verantwortlich im Sinne der Datenschutz-Grundverordnung (DSGVO) ist:<br />
          {#each addressLines(legal) as line}{line}<br />{/each}
          E-Mail: {#if mail}<a href={mail}>{legal.email}</a>{:else}{legal.email}{/if}
          {#if legal.phone}<br />Telefon: {legal.phone}{/if}
        </p>
        <p>Ein Datenschutzbeauftragter ist nicht bestellt, da dies nach den gesetzlichen Vorgaben nicht erforderlich ist.</p>

        <h2 class="nx-h2">2. Hosting und Server-Protokolle</h2>
        <p>
          {SITE_NAME} wird auf einem Server
          {#if legal.hostingProvider}bei {legal.hostingProvider}{:else}eines Hosting-Anbieters{/if}{#if legal.hostingRegion} (Standort: {legal.hostingRegion}){/if} betrieben.
          Der Anbieter verarbeitet Daten in unserem Auftrag. Mit ihm besteht ein
          Vertrag zur Auftragsverarbeitung nach Art. 28 DSGVO.
        </p>
        <p>
          Beim Aufruf einer Seite verarbeitet der Webserver technisch notwendig die IP-Adresse deines Geräts, damit die Seite bei dir
          ankommt. Der Server schreibt außerdem Protokolle mit diesen Angaben: gekürzte IP-Adresse (bei IPv4 ohne die letzte Zahl,
          bei IPv6 ohne die letzten 80 Bit), Datum und Uhrzeit, aufgerufener Pfad, Antwortstatus, übertragene Datenmenge und
          Browserkennung (User-Agent). Die Protokolle dienen dem stabilen und sicheren Betrieb, der Fehlersuche und der Abwehr von
          Missbrauch. Sie werden nicht mit anderen Daten zusammengeführt.
        </p>
        <p>
          Die Protokolle haben eine feste Größenbegrenzung und werden laufend rotiert. Ältere Einträge werden dabei überschrieben,
          in der Regel nach wenigen Tagen bis Wochen. Bei technischen Fehlern kann das Fehlerprotokoll des Servers die vollständige
          IP-Adresse enthalten, auch dieses wird rotiert. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse
          am sicheren und störungsfreien Betrieb).
        </p>

        <h2 class="nx-h2">3. Spielen am Tisch</h2>
        <p>
          Zum Spielen gibst du einen Spielnamen an. Du kannst ihn frei wählen, ein Klarname ist nicht nötig. Auf dem Server werden
          gespeichert: Spielname, Tisch-Code, Rolle (Spieler oder Zuschauer), Verbindungsstatus mit dem Zeitpunkt der letzten
          Aktivität, ein Hash deines Sitzungs-Tokens, bei einem Tisch mit Passwort ein Hash des Passworts, der aktuelle Spielstand samt
          Karten und das Spielprotokoll. Der Tisch-Chat liegt nur im Arbeitsspeicher des Servers.
        </p>
        <p>
          Die anderen Personen am Tisch sehen deinen Spielnamen, deine Spielzüge und deine Chat-Nachrichten. Der Betreiber kann zur
          Betreuung des Dienstes einen Tisch beobachten, beenden oder eine Nachricht an ihn senden (Abschnitt 8). Stellt die Gastgeberin
          oder der Gastgeber einen Tisch auf „öffentlich“, erscheinen Tisch-Code, Spielnamen der sitzenden Personen und die Regeln
          für alle Besucher in der Liste offener Tische, solange der Tisch auf Mitspieler wartet.
        </p>
        <p>
          Zweck ist die Durchführung des Spiels. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO (Bereitstellung des Spiels, das du
          nutzen möchtest), ergänzend lit. f. Ein Tisch, an dem 12 Stunden nichts passiert, wird automatisch geschlossen. Dabei
          werden Mitgliedsdaten, Spielstand, Protokoll und Chat gelöscht. Ein Neustart des Servers löscht den Chat ebenfalls.
          Ohne Spielnamen ist der Beitritt zu einem Tisch nicht möglich.
        </p>

        <h2 class="nx-h2">4. Speicherung im Browser</h2>
        <p>
          {SITE_NAME} speichert Einträge im lokalen Speicher (<code>localStorage</code>) deines Browsers. Es sind keine Cookies,
          und die Einträge enthalten außer den unten genannten Angaben nichts zu deiner Person:
        </p>
        <ul>
          <li>das Sitzungs-Token je Tisch (<code>doko.sessions.v1</code>), damit du nach einem Neuladen an deinem Platz bleibst,</li>
          <li>den zuletzt verwendeten Spielnamen (<code>doko.name.v1</code>),</li>
          <li>eine zufällige Kennung für Daumen bei Verbesserungsvorschlägen (<code>doko.client.v1</code>),</li>
          <li>
            deine Wahl zwischen hellem und dunklem Tisch (<code>doko.theme.v1</code>), sobald du am Tisch umschaltest. Der dunkle Tisch
            betrifft nur die Tischansicht,
          </li>
          <li>
            nur wenn du den Online-Status selbst einschaltest (Abschnitt 6): deinen Freundescode, deinen Anzeigenamen und die von
            dir eingetragene Freundesliste (<code>doko.friends.v1</code>).
          </li>
        </ul>
        <p>
          Zusätzlich merkt sich dein Browser im Tab-Speicher (<code>sessionStorage</code>), dass du einen Hinweisbanner des Betreibers
          geschlossen hast (<code>doko.banner.closed</code>). Dieser Eintrag verschwindet, wenn du den Tab schließt.
        </p>
        <p>
          Diese Speicherung ist für die von dir gewünschten Funktionen erforderlich oder geschieht erst auf deine ausdrückliche
          Entscheidung und braucht deshalb keine gesonderte Einwilligung (§ 25 Abs. 2 Nr. 2 TDDDG). Die nachfolgende Verarbeitung
          stützt sich auf Art. 6 Abs. 1 lit. a, b und f DSGVO. Du kannst die Einträge jederzeit in den Einstellungen deines Browsers
          löschen. Dann erkennt dich der Tisch nicht wieder, Daumen lassen sich erneut vergeben, und Freundescode und Liste sind weg.
        </p>

        <h2 class="nx-h2">5. Verbesserungsvorschläge, Daumen und Missbrauchsschutz</h2>
        <p>
          Titel und Beschreibung eines Vorschlags werden gespeichert und sind für alle Besucher sichtbar. Bitte trage dort keine
          persönlichen Daten ein. Der Betreiber kann Vorschläge ausblenden oder löschen. Sie bleiben bis dahin gespeichert.
        </p>
        <p>
          Damit jeder Vorschlag je Person nur einen Daumen erhält, sendet dein Browser seine zufällige Kennung an den Server. Dort
          wird nur ein Hash davon gespeichert, nicht die Kennung selbst und keine IP-Adresse.
        </p>
        <p>
          Zum Schutz vor automatisierten Eingaben nutzt das Formular ein selbst erzeugtes Captcha (ohne Fremddienst) und ein
          verstecktes Feld. Zur Begrenzung der Anfragen je Stunde zählt der Server die Anfragen pro IP-Adresse und pro Browserkennung (als
          Hash) im Arbeitsspeicher. Der Zähler erfasst nur die letzte Stunde, wird nicht dauerhaft gespeichert und verschwindet bei
          einem Neustart des Servers. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einem missbrauchsfreien Betrieb und an Rückmeldungen zur
          Weiterentwicklung).
        </p>

        <h2 class="nx-h2">6. Freiwilliger Online-Status („Wer ist online“) – ohne Konto</h2>
        <p>
          Du kannst freiwillig zeigen, dass du online bist, und mit denselben Leuten wieder spielen. Das ist <strong>standardmäßig
          ausgeschaltet</strong>. Niemand muss preisgeben, dass er online ist. Ein Konto oder eine Registrierung gibt es dafür nicht.
        </p>
        <p>Wenn du die Funktion einschaltest (Haken im Dialog „Wer ist online?“), geschieht Folgendes:</p>
        <ul>
          <li>
            Dein Browser erzeugt einen zufälligen <strong>Freundescode</strong> (10 Zeichen). Du wählst einen
            <strong>Anzeigenamen</strong>. Beides und deine Freundesliste liegen nur in deinem Browser (Abschnitt 4).
          </li>
          <li>
            Solange du online bist, hält der Server Freundescode, Anzeigenamen, die technische Verbindungskennung und die Codes
            deiner eingetragenen Freunde ausschließlich im <strong>Arbeitsspeicher</strong>. Beim Trennen der Verbindung, beim
            Ausschalten und bei einem Neustart ist das alles gelöscht. Es wird nichts in der Datenbank gespeichert und nichts
            protokolliert.
          </li>
          <li>
            Sichtbar bist du nur für Personen, die deinen Freundescode kennen und in ihre eigene Liste eingetragen haben, und nur,
            wenn sie selbst auch sichtbar sind. Wer selbst nicht sichtbar ist, sieht auch niemanden. Der Code ist so lang, dass er
            sich nicht erraten lässt. Gib ihn nur an Personen weiter, die dich sehen dürfen.
          </li>
          <li>
            Lädst du einen Freund an deinen Tisch ein, erhält er, wenn er online ist, deinen Anzeigenamen, den Tisch-Code und den
            Hinweis, ob der Tisch ein Passwort hat. Zum Schutz vor Missbrauch zählt der Server die Einladungen je Verbindung für
            kurze Zeit im Arbeitsspeicher.
          </li>
        </ul>
        <p>
          Rechtsgrundlage ist deine Einwilligung (Art. 6 Abs. 1 lit. a DSGVO) durch das Einschalten. Du kannst sie jederzeit mit Wirkung
          für die Zukunft widerrufen, indem du den Online-Status ausschaltest. Du bist dann sofort unsichtbar. Mit „Code &amp; Liste
          löschen“ entfernst du außerdem alle Angaben aus deinem Browser. Der Betreiber kann die Funktion für alle abschalten. Die
          IP-Adresse deines Geräts wird wie bei jeder Verbindung technisch verarbeitet (Abschnitt 2).
        </p>

        <h2 class="nx-h2">7. Nutzungsstatistik, Auswertungen, Fehler-Log und Systemstatus</h2>
        <p>
          Für jeden Tisch zählt der Server nur Zeitpunkte (Anlage, Start, letzte Aktivität), die Zahl der Menschen und Bots am Tisch
          und die Zahl der Spiele und Runden, zusammen mit dem Tisch-Code. Namen, Spielinhalte und Chat gehören nicht dazu. Die
          Zahlen lassen sich keiner Person zuordnen und bleiben zur Auswertung der Nutzung gespeichert.
        </p>
        <p>
          Für Auswertungen (Spiele pro Tag, Spitzenzeiten, durchschnittliche Spieldauer, Abbruchquote) speichert der Server zu jedem
          beendeten Spiel nur den Zeitpunkt, die Dauer und die Zahl der Menschen am Tisch. Es gibt keine Namen, keinen Tisch-Code,
          keine Karten und keine IP-Adressen in diesen Einträgen. Sie werden nach 400 Tagen gelöscht.
        </p>
        <p>
          Treten technische Fehler auf, legt der Server einen Eintrag im Fehler-Log an: Zeitpunkt, Quelle, aufgerufener Pfad ohne
          Parameter, Fehlerart, gekürzte Fehlermeldung und technischer Ablauf (Stacktrace). Gleiche Fehler werden gezählt statt
          mehrfach gespeichert. Es werden keine IP-Adressen, Anfrageinhalte oder Chat-Texte aufgenommen. Das Log hält höchstens 300
          Einträge und löscht Einträge nach 30 Tagen. Der Systemstatus zeigt dem Betreiber Datenbankgröße, Programmversion, Zeitpunkt
          des letzten Deploys, Laufzeit und Zähler (z. B. offene Verbindungen) ohne Personenbezug.
        </p>
        <p>
          Zweck ist der stabile, sichere und bedarfsgerechte Betrieb und die Weiterentwicklung. Rechtsgrundlage ist Art. 6 Abs. 1
          lit. f DSGVO.
        </p>

        <h2 class="nx-h2">8. Betreiber-Werkzeuge (Live-Übersicht, Zuschauen, Nachrichten, Beenden)</h2>
        <p>
          Der Betreiber hat nach Anmeldung mit einem Passwort Zugriff auf ein Dashboard. Es zeigt in Echtzeit die offenen Tische mit
          Tisch-Code, Spielnamen der Sitzenden, Verbindungsstatus, Spielfortschritt, Zahl der Zuschauer und die Zahl der verbundenen
          Spieler. Der Betreiber kann
        </p>
        <ul>
          <li>
            einen Tisch <strong>beobachten</strong>. Er erscheint dann für alle am Tisch sichtbar in der Liste der Zuschauer mit dem
            Namen „Betreiber“ und sieht das Spiel wie ein Zuschauer, auch die Karten der Spieler. Das geschieht nicht heimlich.
          </li>
          <li>eine <strong>Nachricht</strong> an alle an einem Tisch senden (z. B. zu Wartungsarbeiten),</li>
          <li>
            einen Tisch <strong>beenden</strong>, optional mit einer Nachricht. Dabei werden Mitgliedsdaten, Spielstand und Protokoll
            des Tisches gelöscht (wie in Abschnitt 3 beschrieben).
          </li>
        </ul>
        <p>
          Außerdem kann der Betreiber Design-Einstellungen (Farben, Vorgabe für Hell oder Dunkel am Tisch), einen Hinweisbanner (z. B.
          bei Wartungsarbeiten) und das Ein- und Ausschalten des Online-Status pflegen. Diese Einstellungen enthalten keine
          personenbezogenen Daten. Beim Aufruf einer Seite fragt dein Browser sie vom Server ab (Abschnitt 2).
        </p>
        <p>
          Zweck ist der Betrieb, die Fehlerbehebung, der Support und der Schutz vor Missbrauch. Rechtsgrundlage ist Art. 6 Abs. 1 lit.
          f DSGVO. Der Zugriff ist auf den Betreiber beschränkt.
        </p>

        <h2 class="nx-h2">9. Domain, DNS und Verschlüsselung</h2>
        <p>
          {#if legal.registrar}Die Domain ist bei {legal.registrar} registriert.{:else}Die Domain ist bei einem Domain-Registrar registriert.{/if}
          Der Registrar verarbeitet dabei die Daten des Domain-Inhabers, nicht die Daten der Besucher dieser Seite. Läuft die
          Namensauflösung (DNS) über die Nameserver des Registrars, kann dieser technisch bedingt die Adresse des anfragenden
          DNS-Servers verarbeiten. Inhalte der Website erhält er nicht.
        </p>
        <p>Die Übertragung zwischen deinem Browser und der Seite ist per TLS (https) verschlüsselt.</p>

        <h2 class="nx-h2">10. Externe Links</h2>
        <p>
          Im Fuß der Seite und in einzelnen Texten führen Links zu externen Seiten, etwa zu GitHub und zum Deutschen
          Doppelkopf-Verband. Erst wenn du einen Link anklickst, wird eine Verbindung zu dem jeweiligen Anbieter aufgebaut und deine
          IP-Adresse an ihn übermittelt. Für die Datenverarbeitung dort gelten dessen Datenschutzhinweise.
        </p>

        <h2 class="nx-h2">11. Empfänger und Drittländer</h2>
        <p>
          Empfänger deiner Daten ist nur der oben genannte Hosting-Anbieter als Auftragsverarbeiter. Eine Weitergabe an sonstige
          Dritte findet nicht statt. Gehört der Hosting-Anbieter zu einem Konzern mit Sitz außerhalb der EU, stützt sich eine dabei
          mögliche Übermittlung in ein Drittland auf einen Angemessenheitsbeschluss der EU-Kommission (EU-US Data Privacy Framework)
          oder auf EU-Standardvertragsklauseln (Art. 44 ff. DSGVO).
        </p>

        <h2 class="nx-h2">12. Deine Rechte</h2>
        <p>Du hast gegenüber dem Verantwortlichen das Recht auf</p>
        <ul>
          <li>Auskunft über die zu dir gespeicherten Daten (Art. 15 DSGVO),</li>
          <li>Berichtigung unrichtiger Daten (Art. 16 DSGVO),</li>
          <li>Löschung (Art. 17 DSGVO),</li>
          <li>Einschränkung der Verarbeitung (Art. 18 DSGVO),</li>
          <li>Datenübertragbarkeit (Art. 20 DSGVO).</li>
          <li>Widerruf einer Einwilligung mit Wirkung für die Zukunft (Art. 7 Abs. 3 DSGVO), etwa durch Ausschalten des Online-Status.</li>
        </ul>
        <p>
          <strong>Widerspruchsrecht (Art. 21 DSGVO):</strong> Soweit wir Daten auf Grundlage berechtigter Interessen (Art. 6 Abs. 1
          lit. f DSGVO) verarbeiten, kannst du jederzeit aus Gründen, die sich aus deiner besonderen Situation ergeben, dagegen
          Widerspruch einlegen.
        </p>
        <p>
          Da {SITE_NAME} keine Konten führt, können wir dich ohne zusätzliche Angaben nicht erkennen (Art. 11 DSGVO). Nenne uns bei
          einer Anfrage bitte Spielname und Tisch-Code oder den Text deines Vorschlags, damit wir die Daten finden. Schreibe dazu an
          {#if mail}<a href={mail}>{legal.email}</a>{:else}{legal.email}{/if}.
        </p>
        <p>
          Außerdem kannst du dich bei einer Datenschutz-Aufsichtsbehörde beschweren (Art. 77 DSGVO), zum Beispiel bei der für deinen
          Wohnort oder unseren Sitz zuständigen Landesbehörde. Eine Liste findest du bei der
          <a href="https://www.bfdi.bund.de/DE/Service/Anschriften/Laender/Laender-node.html" target="_blank" rel="noopener noreferrer"
            >Bundesbeauftragten für den Datenschutz und die Informationsfreiheit</a
          >.
        </p>

        <h2 class="nx-h2">13. Pflicht zur Bereitstellung, automatisierte Entscheidungen</h2>
        <p>
          Du bist weder gesetzlich noch vertraglich verpflichtet, Daten bereitzustellen. Ohne Spielnamen kannst du allerdings keinem
          Tisch beitreten. Eine automatisierte Entscheidungsfindung einschließlich Profiling findet nicht statt. Die Computer-Mitspieler
          (Bots) treffen nur Spielentscheidungen und werten keine Personendaten aus.
        </p>

        <h2 class="nx-h2">14. Änderungen</h2>
        <p>
          Wir passen diese Erklärung an, wenn sich das Angebot ändert, etwa durch neue Funktionen. Es gilt die jeweils hier
          veröffentlichte Fassung.
        </p>
      </div>
    {/if}
  {/if}
</PageShell>

<style>
  .legal :global(h2) {
    margin-top: 24px;
  }
  .legal :global(h2:first-of-type) {
    margin-top: 8px;
  }
  .legal :global(ul) {
    margin: 0 0 14px;
    padding-left: 1.4rem;
  }
  .legal :global(li) {
    margin-bottom: 6px;
  }
  .legal :global(address) {
    font-style: normal;
    margin: 0 0 14px;
  }
  .legal :global(a) {
    color: inherit;
    text-decoration-thickness: 2px;
    text-underline-offset: 3px;
  }
  .legal :global(code) {
    font-family: var(--font-mono);
    font-size: 0.85em;
    overflow-wrap: anywhere;
  }
</style>
