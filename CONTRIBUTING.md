# Mitwirken

Schön, dass du helfen möchtest! Fehlerberichte, Verbesserungsvorschläge, Fragen, Dokumentation und Code sind willkommen.
Das Projekt ist in der **Beta-Phase**; Rückmeldungen aus echten Spielrunden sind besonders wertvoll.

Es gelten die [Verhaltensregeln](CODE_OF_CONDUCT.md). Sicherheitslücken bitte **nicht** öffentlich melden, sondern wie in [SECURITY.md](SECURITY.md) beschrieben.

## Fehler melden und Ideen einbringen

- **Ideen und Wünsche** kannst du ohne GitHub-Konto über das Formular am Ende der Website einreichen oder als [Issue](https://github.com/jacquesbach/doppelkopf/issues/new/choose) (Vorlage „Verbesserungsvorschlag“).
- **Fehler:** Beschreibe kurz, was du getan hast, was du erwartet hast und was stattdessen passiert ist. Browser, Gerät und (falls ein bestimmter Tisch betroffen war) der Tisch-Code helfen. Schreibe **keine Platz-Codes oder Passwörter** in ein Ticket.
- **Regelfragen:** Nenne den Abschnitt der DDV-Turnierspielregeln oder beschreibe die Haus- bzw. Kneipenregel, die du meinst. Die umgesetzten Regeln stehen in [docs/DDV_REGELMATRIX.md](docs/DDV_REGELMATRIX.md).

## Code beitragen

1. Repository forken, Zweig anlegen (`git checkout -b mein-zweig`).
2. Entwicklungsumgebung einrichten: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) (Voraussetzungen, Starten, Tests).
3. Änderung umsetzen, Tests schreiben, Tests laufen lassen:

   ```bash
   npm test && npm run check:svelte
   cd backend
   python -m unittest discover -s tests/rules -t .
   python -m unittest discover -s tests/service -t .
   ```

4. Pull Request nach `main` öffnen. Die Vorlage enthält eine Prüfliste. Die CI muss grün sein.

Kleine, abgeschlossene Änderungen lassen sich leichter prüfen als große. Bei größeren Vorhaben lohnt sich vorab ein Issue, damit wir die Richtung klären.

### Was zu beachten ist

- **Regeln:** Änderungen an den Spielregeln brauchen einen Verweis auf den Paragraphen der DDV-Turnierspielregeln (oder eine Beschreibung der Hausregel), einen **Test** und eine Zeile in der [Regelmatrix](docs/DDV_REGELMATRIX.md). Regeln leben im Regelkern (`backend/app/rules`), nirgends sonst.
- **Datenschutz:** Das Projekt speichert bewusst so wenig wie möglich. Wird etwas Neues gespeichert (Datenbank, Browser, Protokoll), müssen [docs/PRIVACY.md](docs/PRIVACY.md) und die Datenschutzerklärung (`src/pages/Legal.svelte`) angepasst werden. Daten an Dritte (Fremddienste, externe Schriften) sind nicht vorgesehen.
- **Sichten:** Fremde Handkarten und verdeckte Informationen dürfen den Server nie verlassen. Wer Sichten ändert, ergänzt den Lecktest (`backend/tests/service/test_view_leaks.py`).
- **Schnittstelle:** Neue oder geänderte Routen gehören in [docs/API.md](docs/API.md), neue Einstellungen in [docs/CONFIGURATION.md](docs/CONFIGURATION.md) und `.env.example`.
- **Sprache und Stil:** Oberfläche, Kommentare und Dokumentation sind auf Deutsch, Bezeichner im Code auf Englisch. Frontend mit `npm run format` formatieren.
- **Abhängigkeiten:** Neue Abhängigkeiten sparsam wählen und begründen. Das Projekt kommt bewusst mit wenigen aus.

## Lizenz

Mit deinem Beitrag erklärst du dich einverstanden, dass er unter der [MIT-Lizenz](LICENSE) des Projekts veröffentlicht wird.
