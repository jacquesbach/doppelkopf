"""Gemeinschaftsfunktionen und Betreiber-Backend: Verbesserungsvorschlaege, Klassiker-Sprueche, Statistik, Tischuebersicht.

Die Logik ist flask- und datenbankfrei (Dienste + kleine Speicher-Schnittstellen); ``api.py`` ist die HTTP-Huelle,
``sql.py`` die SQLAlchemy-Umsetzung. Dadurch laeuft die gesamte Logik samt HTTP-Schicht in Tests ohne Datenbank.
"""
