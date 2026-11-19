"""SQL-Umsetzung von Vorschlaegen, Spruechen, Statistik und Tischuebersicht (mit echtem SQLAlchemy/SQLite)."""
import random

import pytest

from app import create_app, db
from app.community.sql import SqlPhrases, SqlStats, SqlSuggestions, seed_default_phrases
from app.community.phrases import DEFAULT_PHRASES
from app.models import Phrase, Setting, TableLog

PASSWORD = "betreiber-passwort"


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "PACED_BOTS": False, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'c.sqlite'}",
                      "SECRET_KEY": "test", "ADMIN_PASSWORD": PASSWORD, "CORS_ORIGINS": ["http://localhost:5173"]})
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def admin(client):
    token = client.post("/api/admin/login", json={"password": PASSWORD}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_default_phrases_seeded_once(app):
    with app.app_context():
        assert [p["text"] for p in SqlPhrases().list()] == list(DEFAULT_PHRASES)
        for p in Phrase.query.all():
            db.session.delete(p)
        db.session.commit()
        seed_default_phrases()                      # Marker gesetzt: geloeschte Sprueche kommen nicht zurueck
        assert Phrase.query.count() == 0
        assert db.session.get(Setting, "phrases_seeded") is not None


def test_phrase_order_and_crud_via_sql(app):
    with app.app_context():
        store = SqlPhrases()
        first = store.list()[0]["id"]
        added = store.add("Neu hinten")
        assert store.list()[-1]["id"] == added["id"]
        store.reorder([added["id"]] + [p["id"] for p in store.list() if p["id"] != added["id"]])
        assert store.list()[0]["id"] == added["id"]
        assert store.update(first, "Geaendert") and store.delete(added["id"])
        assert not store.delete(added["id"])


def test_votes_unique_toggle_and_counts(app):
    with app.app_context():
        store = SqlSuggestions()
        item = store.add("Titel", "Beschreibung, lang genug.", 1_800_000_000.0)
        assert store.toggle_vote(item["id"], "a" * 32) == {"votes": 1, "voted": True}
        assert store.toggle_vote(item["id"], "b" * 32) == {"votes": 2, "voted": True}
        assert store.toggle_vote(item["id"], "a" * 32) == {"votes": 1, "voted": False}
        listed = store.list(False, "b" * 32)
        assert (listed[0]["votes"], listed[0]["voted"]) == (1, True)
        store.set_status(item["id"], "hidden")
        assert store.list(False, None) == [] and len(store.list(True, None)) == 1
        assert store.toggle_vote(item["id"], "c" * 32) is None
        assert store.delete(item["id"]) and store.list(True, None) == []


def test_stats_recorder_roundtrip(app):
    with app.app_context():
        st = SqlStats()
        st.table_created("ABC234", now=1000)
        st.round_started("ABC234", 1, 3, now=1100)
        st.game_finished("ABC234", now=1500)
        (log,) = st.logs()
        assert (log["createdAt"], log["startedAt"], log["lastActivityAt"], log["games"], log["humans"]) == (1000, 1100, 1500, 1, 1)
        st.round_started("UNBEKANNT", 2, 2)        # darf nichts kaputt machen
        assert TableLog.query.count() == 1


def test_http_flow_with_real_app(client):
    assert client.get("/api/phrases").get_json()["phrases"][0]["text"] == DEFAULT_PHRASES[0]
    headers = admin(client)
    assert client.get("/api/admin/stats", headers=headers).get_json()["tablesTotal"] == 0
    created = client.post("/api/rooms", json={"name": "Ada"}).get_json()
    code = created["room"]["code"]
    stats = client.get("/api/admin/stats", headers=headers).get_json()
    assert stats["tablesTotal"] == 1 and stats["tablesNeverStarted"] == 1
    tables = client.get("/api/admin/tables", headers=headers).get_json()
    assert [t["code"] for t in tables["tables"]] == [code] and tables["tables"][0]["humans"] == 1
    # Spiel starten: Statistik merkt sich Menschen/Bots und den Start
    token = created["token"]
    for _ in range(3):
        assert client.post(f"/api/rooms/{code}/bots", json={"token": token}).status_code in (200, 201)
    assert client.post(f"/api/rooms/{code}/ready", json={"token": token, "ready": True}).status_code == 200
    started = client.post(f"/api/rooms/{code}/start", json={"token": token}, headers={"X-Session-Token": token})
    assert started.status_code == 201, started.get_json()
    stats = client.get("/api/admin/stats", headers=headers).get_json()
    assert stats["tablesStarted"] == 1 and stats["againstBotsOnly"]["tables"] == 1
    # Vorschlag: Captcha ist signiert, ohne Loesung wird abgelehnt
    cap = client.get("/api/captcha").get_json()
    bad = client.post("/api/suggestions", json={"title": "Neue Idee", "description": "Eine gute Idee, lang genug.",
                                                 "captchaToken": cap["token"], "captchaAnswer": "XXXXX"})
    assert bad.status_code == 400 and bad.get_json()["code"] == "captcha_wrong"
