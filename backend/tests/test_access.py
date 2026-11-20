"""Raumzugang: Platz-Code beim Wiedereinstieg, Limits gegen Durchprobieren, Passwort-Mindestlaenge (mit Datenbank)."""
from datetime import timedelta

import pytest

from app import create_app, db
from app.models import Member, utcnow


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "RATE_LIMITS_IN_TESTS": True, "CREATE_PER_HOUR": 3, "PACED_BOTS": False,
                      "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'access.sqlite'}", "SECRET_KEY": "test",
                      "CORS_ORIGINS": ["http://localhost:5173"]})
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def disconnect(app, name):
    with app.app_context():
        member = Member.query.filter_by(name=name).first()
        member.connected = False
        member.last_seen_at = utcnow() - timedelta(minutes=2)
        db.session.commit()


def table_with_bert(client, password=None):
    body = {"name": "Ada"}
    if password:
        body["password"] = password
    host = client.post("/api/rooms", json=body).get_json()
    code = host["room"]["code"]
    bert = client.post(f"/api/rooms/{code}/join", json={"name": "Bert", "password": password}).get_json()
    return code, host["token"], bert["token"]


def test_password_needs_six_characters(client):
    assert client.post("/api/rooms", json={"name": "Ada", "password": "12345"}).status_code == 400
    assert client.post("/api/rooms", json={"name": "Ada", "password": "123456"}).status_code == 201


def test_rejoin_needs_the_seat_code(app, client):
    code, host_token, bert_token = table_with_bert(client)
    own = client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": bert_token})
    assert own.status_code == 200
    seat_code = own.get_json()["code"]
    assert len(seat_code) == 9 and seat_code[4] == "-"
    disconnect(app, "Bert")
    for body in ({"name": "Bert"}, {"name": "Bert", "seatCode": "AAAA-AAAA"}, {"name": "Bert", "seatCode": ""}):
        assert client.post(f"/api/rooms/{code}/rejoin", json=body).status_code == 403
    ok = client.post(f"/api/rooms/{code}/rejoin", json={"name": "bert", "seatCode": seat_code.lower()})
    assert ok.status_code == 200
    new_token = ok.get_json()["token"]
    assert new_token != bert_token
    assert client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": bert_token}).status_code == 403   # altes Token wertlos
    assert client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": new_token}).get_json()["code"] == seat_code


def test_rejoin_refused_while_the_player_is_connected(app, client):
    code, _, bert_token = table_with_bert(client)
    seat_code = client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": bert_token}).get_json()["code"]
    assert client.post(f"/api/rooms/{code}/rejoin", json={"name": "Bert", "seatCode": seat_code}).status_code == 409


def test_rejoin_still_checks_the_table_password(app, client):
    code, _, bert_token = table_with_bert(client, password="geheim1")
    seat_code = client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": bert_token}).get_json()["code"]
    disconnect(app, "Bert")
    assert client.post(f"/api/rooms/{code}/rejoin", json={"name": "Bert", "seatCode": seat_code, "password": "falsch"}).status_code == 403
    assert client.post(f"/api/rooms/{code}/rejoin", json={"name": "Bert", "seatCode": seat_code, "password": "geheim1"}).status_code == 200


def test_only_the_host_sees_all_seat_codes(client):
    code, host_token, bert_token = table_with_bert(client)
    assert client.get(f"/api/rooms/{code}/seat-codes", headers={"X-Session-Token": bert_token}).status_code == 403
    assert client.get(f"/api/rooms/{code}/seat-codes").status_code == 403
    seats = client.get(f"/api/rooms/{code}/seat-codes", headers={"X-Session-Token": host_token}).get_json()["seats"]
    assert [s["name"] for s in seats] == ["Ada", "Bert"]
    own = client.get(f"/api/rooms/{code}/seat-code", headers={"X-Session-Token": bert_token}).get_json()["code"]
    assert seats[1]["code"] == own
    assert client.get(f"/api/rooms/{code}/seat-code").status_code == 403


def test_wrong_attempts_are_blocked_per_table(client):
    code, _, _ = table_with_bert(client, password="geheim1")
    for _ in range(8):
        assert client.post(f"/api/rooms/{code}/join", json={"name": "Eve", "password": "falsch"}).status_code == 403
    blocked = client.post(f"/api/rooms/{code}/join", json={"name": "Eve", "password": "geheim1"})
    assert blocked.status_code == 429                                            # auch das richtige Passwort wird jetzt gebremst
    assert client.post(f"/api/rooms/{code}/rejoin", json={"name": "Bert", "seatCode": "AAAA-AAAA"}).status_code == 429
    other = client.post("/api/rooms", json={"name": "Zoe"}).get_json()["room"]["code"]
    assert client.post(f"/api/rooms/{other}/join", json={"name": "Max"}).status_code == 201   # anderer Tisch unberuehrt


def test_guessing_table_codes_is_blocked_but_members_keep_playing(client):
    code, _, bert_token = table_with_bert(client)
    guesses = [f"ZZZZ{a}{b}" for a in "23456789" for b in "23456789"][:20]
    for guess in guesses:
        assert client.get(f"/api/rooms/{guess}").status_code == 404
    assert client.get("/api/rooms/ZZZZ99").status_code == 429
    assert client.get(f"/api/rooms/{code}").status_code == 429                                  # Fremde erfahren auch von echten nichts
    mine = client.get(f"/api/rooms/{code}", headers={"X-Session-Token": bert_token})
    assert mine.status_code == 200


def test_stale_tab_of_a_closed_table_does_not_lock_anyone_out(client):
    for _ in range(100):
        assert client.get("/api/rooms/GONE22").status_code == 404                               # derselbe Code zaehlt nur einmal
    assert client.get("/api/rooms/OTHR22").status_code == 404


def test_new_tables_per_hour_are_limited(client):
    for _ in range(3):
        assert client.post("/api/rooms", json={"name": "Ada"}).status_code == 201
    assert client.post("/api/rooms", json={"name": "Ada"}).status_code == 429
