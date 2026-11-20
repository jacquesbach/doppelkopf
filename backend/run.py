import os
from app import create_app, socketio

app = create_app({"SECRET_KEY": os.environ.get("SECRET_KEY", "dev-only-change-me"),
                  "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URL", "sqlite:///doppelkopf.sqlite3"),
                  "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
                  # Betreiber-Backend (/admin): ohne ADMIN_PASSWORD ist es abgeschaltet
                  "ADMIN_PASSWORD": os.environ.get("ADMIN_PASSWORD", ""),
                  # hinter nginx: Besucheradresse aus X-Forwarded-For (fuer Begrenzungen) verwenden
                  "TRUST_PROXY": os.environ.get("TRUST_PROXY") == "1",
                  # neue Tische je Adresse und Stunde (Schutz vor Missbrauch)
                  "CREATE_PER_HOUR": int(os.environ.get("CREATE_PER_HOUR") or 30)})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("BACKEND_PORT") or os.environ.get("PORT") or 8181),
                 debug=os.environ.get("FLASK_DEBUG") == "1",
                 allow_unsafe_werkzeug=True)  # Einzelprozess-Betrieb (Docker); ohne dieses Flag startet SocketIO nicht   # Debugger nur auf ausdruecklichen Wunsch
