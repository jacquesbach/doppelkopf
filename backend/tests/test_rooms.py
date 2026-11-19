import pytest
from app import create_app, db
from app.models import Room, Member


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "PACED_BOTS": False, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.sqlite'}",
                      "SECRET_KEY": "test", "CORS_ORIGINS": ["http://localhost:5173"]})
    with app.test_client() as client:
        yield client
    with app.app_context():
        db.drop_all()


def test_create_room_and_join(client):
    created = client.post("/api/rooms", json={"name": "Ada"})
    assert created.status_code == 201
    payload = created.get_json()
    code = payload["room"]["code"]
    assert payload["room"]["playerCount"] == 1
    joined = client.post(f"/api/rooms/{code}/join", json={"name": "Bert", "role": "player"})
    assert joined.status_code == 201
    assert joined.get_json()["room"]["playerCount"] == 2


def test_password_protects_room(client):
    created = client.post("/api/rooms", json={"name": "Ada", "password": "geheim"}).get_json()
    code = created["room"]["code"]
    rejected = client.post(f"/api/rooms/{code}/join", json={"name": "Bert", "password": "falsch"})
    assert rejected.status_code == 403
    accepted = client.post(f"/api/rooms/{code}/join", json={"name": "Bert", "password": "geheim"})
    assert accepted.status_code == 201


def test_public_tables_list_and_visibility(client):
    private = client.post("/api/rooms", json={"name": "Ada"}).get_json()
    public = client.post("/api/rooms", json={"name": "Bert", "public": True, "password": "geheim"}).get_json()
    listed = client.get("/api/rooms/public").get_json()["rooms"]
    assert [r["code"] for r in listed] == [public["room"]["code"]]
    entry = listed[0]
    assert entry["host"] == "Bert" and entry["hasPassword"] is True and entry["playerCount"] == 1
    assert "settings" in entry and "token" not in entry
    # Host schaltet den privaten Tisch oeffentlich; fremde Sitzung darf das nicht
    code = private["room"]["code"]
    joined = client.post(f"/api/rooms/{code}/join", json={"name": "Cora"}).get_json()
    denied = client.post(f"/api/rooms/{code}/visibility", json={"token": joined["token"], "public": True})
    assert denied.status_code == 403
    ok = client.post(f"/api/rooms/{code}/visibility", json={"token": private["token"], "public": True})
    assert ok.status_code == 200 and ok.get_json()["room"]["isPublic"] is True
    assert {r["code"] for r in client.get("/api/rooms/public").get_json()["rooms"]} == {code, public["room"]["code"]}


def test_public_list_hides_full_and_started_tables(client):
    created = client.post("/api/rooms", json={"name": "Ada", "public": True}).get_json()
    code, token = created["room"]["code"], created["token"]
    client.post(f"/api/rooms/{code}/bots", json={"token": token})        # Tisch voll -> nicht mehr gelistet
    assert client.get("/api/rooms/public").get_json()["rooms"] == []


def test_takeover_setting_is_part_of_the_room_and_host_only(client):
    created = client.post("/api/rooms", json={"name": "Ada"}).get_json()
    code, token = created["room"]["code"], created["token"]
    assert created["room"]["botTakeover"] == 180                       # Standard: 3 Minuten
    joined = client.post(f"/api/rooms/{code}/join", json={"name": "Bert"}).get_json()
    assert client.post(f"/api/rooms/{code}/takeover", json={"token": joined["token"], "seconds": 0}).status_code == 403
    assert client.post(f"/api/rooms/{code}/takeover", json={"token": token, "seconds": 45}).status_code == 400
    ok = client.post(f"/api/rooms/{code}/takeover", json={"token": token, "seconds": 0})
    assert ok.status_code == 200
    assert client.get(f"/api/rooms/{code}").get_json()["room"]["botTakeover"] == 0


def test_idle_rooms_are_closed_after_twelve_hours(client):
    from datetime import datetime, timedelta, timezone
    from app.housekeeping import close_idle_rooms
    from app.models import GameSnapshot
    old = client.post("/api/rooms", json={"name": "Ada"}).get_json()["room"]["code"]
    fresh = client.post("/api/rooms", json={"name": "Bert"}).get_json()["room"]["code"]
    with client.application.app_context():
        long_ago = datetime.now(timezone.utc) - timedelta(hours=13)
        room = Room.query.filter_by(code=old).first()
        room.created_at = long_ago
        for member in room.members:
            member.joined_at = long_ago
        db.session.commit()
        assert close_idle_rooms() == [old]
        assert Room.query.filter_by(code=old).first() is None
        assert Room.query.filter_by(code=fresh).first() is not None
        assert Member.query.count() == 1                               # Mitglieder des geschlossenen Raums sind weg
        assert GameSnapshot.query.count() == 0
    assert client.get(f"/api/rooms/{old}").status_code == 404
