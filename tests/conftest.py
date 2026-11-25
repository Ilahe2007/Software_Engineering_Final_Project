"""Shared test fixtures. Part B extends this file in PW#3 (users, login, test data).

Every test gets a brand new app with an empty in-memory database.
"""
import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_headers():
    # Temporary until Part B adds real login.
    return {"X-User-Role": "admin"}


@pytest.fixture
def seeded(client, admin_headers):
    """Two room types, three pieces of equipment, three rooms."""
    for name in ("lab", "lecture_hall"):
        client.post("/api/v1/room-types", json={"name": name}, headers=admin_headers)
    for name in ("projector", "computers", "whiteboard"):
        client.post("/api/v1/equipment", json={"name": name}, headers=admin_headers)

    rooms = [
        {"code": "A-101", "building": "A", "capacity": 120, "room_type": "lecture_hall",
         "equipment": ["projector"]},
        {"code": "B-204", "building": "B", "capacity": 30, "room_type": "lab",
         "equipment": ["computers", "projector"]},
        {"code": "B-205", "building": "B", "capacity": 25, "room_type": "lab",
         "equipment": ["whiteboard"]},
    ]
    ids = {}
    for room in rooms:
        response = client.post("/api/v1/rooms", json=room, headers=admin_headers)
        ids[room["code"]] = response.get_json()["id"]
    return ids
