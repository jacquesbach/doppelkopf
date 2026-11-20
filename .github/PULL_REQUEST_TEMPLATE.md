## Was ändert dieser Pull Request?

<!-- Kurz, und warum. Bei Regeländerungen: Abschnitt der DDV-Turnierspielregeln. -->

## Prüfliste

- [ ] Tests laufen: `npm test`, `npm run check:svelte`, Regelkern und Tischschicht (`cd backend && python -m unittest discover -s tests/rules -t . && python -m unittest discover -s tests/service -t .`)
- [ ] Neue oder geänderte Logik hat einen Test
- [ ] Regeländerung: `docs/DDV_REGELMATRIX.md` aktualisiert
- [ ] Neue Route oder Änderung an der Schnittstelle: `docs/API.md` aktualisiert
- [ ] Neue Variable: `.env.example` und `docs/CONFIGURATION.md` (und bei Weg B `deploy.yml`) aktualisiert
- [ ] Datenschutz geprüft: Wird etwas Neues gespeichert? Dann `docs/PRIVACY.md` und `src/pages/Legal.svelte` angepasst
- [ ] Keine fremden Handkarten oder verdeckten Informationen in Sichten (Lecktest ergänzt, falls Sichten geändert)
