# Mitwirken

Fehlerberichte, Verbesserungsvorschläge und Fragen sind willkommen. Bitte beschreibe bei einem Fehler kurz, was du getan hast,
was du erwartet hast und was stattdessen passiert ist (Browser, Gerät und Tisch-Code helfen).

Vor einem Pull Request:

- Regelkern und Tischschicht: `cd backend && python -m unittest discover -s tests/rules -t . && python -m unittest discover -s tests/service -t .`
- Oberfläche: `npm test` und `npm run check:svelte`
- Änderungen an den Spielregeln bitte mit Verweis auf den Paragraphen der DDV-Turnierspielregeln und einem Test.

Es gelten die [Verhaltensregeln](CODE_OF_CONDUCT.md).
