"""Betreiber-Werkzeuge: Design-Einstellungen, Live-Uebersicht, Auswertungen, Fehler-Log und Systemstatus.

Die Fachlogik steht in flask-freien Modulen (``settings``, ``live``, ``insights``, ``errors``, ``system``) und ist ohne
Datenbank testbar; ``sql.py`` verbindet sie mit SQLAlchemy, ``api.py`` ist die HTTP-Schicht (``/api/admin/...``).
"""
