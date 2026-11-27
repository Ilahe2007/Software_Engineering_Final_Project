"""Shared test fixtures (PW#3).

Every test gets a brand new app with an empty in-memory database.

Users and logins:
    make_user(role="student", email=None, password=TEST_PASSWORD) -> User saved in the database
    headers_for(user)  -> {"Authorization": "Bearer <token>"} for that user
    admin_headers, teacher_headers, student_headers -> ready-made logged-in users
    other_student_headers -> a second student, for "not my booking" tests

Data:
    seeded -> {"A-101": id, "B-204": id, "B-205": id}, three rooms with types and equipment
"""
from itertools import count

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.auth.tokens import create_access_token
from app.extensions import db
from app.models import User

TEST_PASSWORD = "correct-horse-battery-staple"
# Real accounts use scrypt. Test users use a cheap hash so the suite stays fast;
# check_password_hash() reads the method from the hash, so login works the same.
_FAST_TEST_HASH = "pbkdf2:sha256:1000"


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()
        db.engine.dispose()  # close the in-memory database now, not whenever the garbage collector runs


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    numbers = count(1)

    def _make_user(role="student", email=None, password=TEST_PASSWORD, full_name=None):
        number = next(numbers)
        user = User(
            email=(email or f"{role}{number}@ufaz.az").lower(),
            full_name=full_name or f"Test {role.title()} {number}",
            password_hash=generate_password_hash(password, method=_FAST_TEST_HASH),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture
def headers_for(app):
    def _headers_for(user):
        token = create_access_token(user, app.config["SECRET_KEY"], app.config["JWT_ACCESS_MINUTES"])
        return {"Authorization": f"Bearer {token}"}

    return _headers_for


@pytest.fixture
def admin_user(make_user):
    return make_user("admin")


@pytest.fixture
def student_user(make_user):
    return make_user("student")


@pytest.fixture
def admin_headers(admin_user, headers_for):
    return headers_for(admin_user)


@pytest.fixture
def teacher_headers(make_user, headers_for):
    return headers_for(make_user("teacher"))


@pytest.fixture
def student_headers(student_user, headers_for):
    return headers_for(student_user)


@pytest.fixture
def other_student_headers(make_user, headers_for):
    return headers_for(make_user("student"))


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
