"""Macht ``app.rules`` / ``app.table`` importierbar, auch wenn Flask-Erweiterungen fehlen.

``app/__init__.py`` importiert Flask-CORS, Flask-SocketIO und Flask-SQLAlchemy. Der Regelkern und die
Tischschicht brauchen sie nicht. Laesst sich ``app`` normal importieren (volle Umgebung), wird das
echte Paket benutzt; sonst wird ein leeres Platzhalter-Paket ``app`` mit dem richtigen Suchpfad
registriert, sodass ``import app.rules`` ohne Ausfuehrung von ``app/__init__.py`` funktioniert.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"


def ensure_app_package() -> None:
    if "app" in sys.modules:
        return
    backend = str(APP_DIR.parent)
    if backend not in sys.path:
        sys.path.insert(0, backend)
    try:
        importlib.import_module("app")
    except ImportError:
        sys.modules.pop("app", None)
        placeholder = types.ModuleType("app")
        placeholder.__path__ = [str(APP_DIR)]
        sys.modules["app"] = placeholder


ensure_app_package()
