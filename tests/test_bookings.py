"""POST /bookings, GET /bookings/me and DELETE /bookings/<id>.

Rooms from the `seeded` fixture:
    A-101  lecture_hall  120 seats  projector
    B-204  lab            30 seats  computers, projector
    B-205  lab            25 seats  whiteboard
"""
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Booking

BOOKINGS = "/api/v1/bookings"
MY_BOOKINGS = "/api/v1/bookings/me"
DAY = "2030-12-02"  # always in the future, so tests do not depend on today's date


def _booking(room_id, start="10:00", end="12:00", **extra):
    body = {
        "room_id": room_id,
        "title": "Robotics club meeting",
        "start": f"{DAY}T{start}",
        "end": f"{DAY}T{end}",
        "attendees": 20,
    }
    body.update(extra)
    return body


def _book(client, headers, room_id, **kwargs):
    return client.post(BOOKINGS, json=_booking(room_id, **kwargs), headers=headers)


# --- Creating ---------------------------------------------------------------------------------


def test_student_books_a_free_room(client, seeded, student_user, student_headers):
    response = _book(client, student_headers, seeded["B-204"])
    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "confirmed"
    assert body["room_code"] == "B-204"
    assert body["user_id"] == student_user.id
    assert body["start"] == f"{DAY}T10:00"


def test_teacher_can_book_too(client, seeded, teacher_headers):
    assert _book(client, teacher_headers, seeded["A-101"], attendees=100).status_code == 201


def test_booking_needs_login(client, seeded):
    assert client.post(BOOKINGS, json=_booking(seeded["B-204"])).status_code == 401


def test_cannot_book_in_someone_elses_name(client, seeded, student_headers, admin_user):
    response = _book(client, student_headers, seeded["B-204"], user_id=admin_user.id, status="confirmed")
    assert response.status_code == 400
    assert response.get_json()["details"]["unknown_fields"] == "not allowed: status, user_id"


def test_booking_reports_every_format_problem_at_once(client, seeded, student_headers):
    body = {"room_id": "B-204", "title": "", "start": "tomorrow", "end": "2030-12-02T12:00+04:00", "attendees": 0}
    response = client.post(BOOKINGS, json=body, headers=student_headers)
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"room_id", "title", "start", "end", "attendees"}


def test_booking_needs_the_required_fields(client, seeded, student_headers):
    response = client.post(BOOKINGS, json={}, headers=student_headers)
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"room_id", "title", "start", "end", "attendees"}


def test_unknown_room(client, seeded, student_headers):
    assert _book(client, student_headers, 9999).status_code == 404


def test_deactivated_room_cannot_be_booked(client, seeded, admin_headers, student_headers):
    client.delete(f"/api/v1/rooms/{seeded['B-205']}", headers=admin_headers)
    response = _book(client, student_headers, seeded["B-205"])
    assert response.status_code == 400
    assert "room_id" in response.get_json()["details"]


# --- The chain of checks ----------------------------------------------------------------------


def test_end_must_be_after_start(client, seeded, student_headers):
    response = _book(client, student_headers, seeded["B-204"], start="12:00", end="10:00")
    assert response.status_code == 400
    assert "end" in response.get_json()["details"]


def test_cannot_book_in_the_past(client, seeded, student_headers):
    body = _booking(seeded["B-204"], start="10:00", end="11:00")
    body.update(start="2020-01-06T10:00", end="2020-01-06T11:00")
    response = client.post(BOOKINGS, json=body, headers=student_headers)
    assert response.status_code == 400
    assert "start" in response.get_json()["details"]


def test_booking_must_stay_inside_opening_hours(client, seeded, student_headers):
    assert _book(client, student_headers, seeded["B-204"], start="07:00", end="09:00").status_code == 400
    assert _book(client, student_headers, seeded["B-204"], start="19:00", end="21:00").status_code == 400


def test_booking_must_be_on_one_day(client, seeded, student_headers):
    body = _booking(seeded["B-204"])
    body["end"] = "2030-12-03T11:00"
    response = client.post(BOOKINGS, json=body, headers=student_headers)
    assert response.status_code == 400
    assert "end" in response.get_json()["details"]


def test_too_many_attendees_for_the_room(client, seeded, student_headers):
    response = _book(client, student_headers, seeded["B-204"], attendees=31)
    assert response.status_code == 400
    assert "30 seats" in response.get_json()["details"]["attendees"]


def test_wrong_room_type(client, seeded, student_headers):
    response = _book(client, student_headers, seeded["B-204"], room_type="lecture_hall")
    assert response.status_code == 400
    assert "room_type" in response.get_json()["details"]


def test_missing_equipment(client, seeded, student_headers):
    response = _book(client, student_headers, seeded["B-205"], equipment=["projector"])
    assert response.status_code == 400
    assert "projector" in response.get_json()["details"]["equipment"]


def test_matching_type_and_equipment_is_accepted(client, seeded, student_headers):
    response = _book(client, student_headers, seeded["B-204"], room_type="lab", equipment=["computers"])
    assert response.status_code == 201


def test_overlapping_booking_is_refused(client, seeded, student_headers, other_student_headers):
    assert _book(client, student_headers, seeded["B-204"], start="10:00", end="12:00").status_code == 201
    response = _book(client, other_student_headers, seeded["B-204"], start="11:00", end="13:00")
    assert response.status_code == 409
    assert "already booked" in response.get_json()["message"]


def test_booking_inside_another_is_refused(client, seeded, student_headers, other_student_headers):
    _book(client, student_headers, seeded["B-204"], start="10:00", end="14:00")
    assert _book(client, other_student_headers, seeded["B-204"], start="11:00", end="12:00").status_code == 409


def test_back_to_back_bookings_do_not_overlap(client, seeded, student_headers, other_student_headers):
    # A range includes its start and excludes its end: 10-12 and 12-13 share no minute.
    assert _book(client, student_headers, seeded["B-204"], start="10:00", end="12:00").status_code == 201
    assert _book(client, other_student_headers, seeded["B-204"], start="12:00", end="13:00").status_code == 201


def test_same_time_in_another_room_is_fine(client, seeded, student_headers, other_student_headers):
    assert _book(client, student_headers, seeded["B-204"]).status_code == 201
    assert _book(client, other_student_headers, seeded["B-205"]).status_code == 201


def test_cancelled_booking_frees_the_slot(client, seeded, student_headers, other_student_headers):
    booking_id = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    client.delete(f"{BOOKINGS}/{booking_id}", headers=student_headers)
    assert _book(client, other_student_headers, seeded["B-204"]).status_code == 201


# --- Listing ----------------------------------------------------------------------------------


def test_my_bookings_shows_only_mine(client, seeded, student_headers, other_student_headers):
    _book(client, student_headers, seeded["B-204"], start="14:00", end="15:00")
    _book(client, student_headers, seeded["B-205"], start="09:00", end="10:00")
    _book(client, other_student_headers, seeded["A-101"])

    body = client.get(MY_BOOKINGS, headers=student_headers).get_json()
    assert body["count"] == 2
    # Soonest first.
    assert [booking["room_code"] for booking in body["bookings"]] == ["B-205", "B-204"]


def test_my_bookings_filter_by_status(client, seeded, student_headers):
    first = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    _book(client, student_headers, seeded["B-205"])
    client.delete(f"{BOOKINGS}/{first}", headers=student_headers)

    cancelled = client.get(f"{MY_BOOKINGS}?status=cancelled", headers=student_headers).get_json()
    assert [booking["id"] for booking in cancelled["bookings"]] == [first]
    assert client.get(f"{MY_BOOKINGS}?status=deleted", headers=student_headers).status_code == 400


def test_my_bookings_needs_login(client):
    assert client.get(MY_BOOKINGS).status_code == 401


# --- Cancelling -------------------------------------------------------------------------------


def test_cancel_my_booking(client, seeded, student_headers):
    booking_id = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    response = client.delete(f"{BOOKINGS}/{booking_id}", headers=student_headers)
    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelled"
    assert response.get_json()["cancelled_at"] is not None


def test_cancel_twice(client, seeded, student_headers):
    booking_id = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    client.delete(f"{BOOKINGS}/{booking_id}", headers=student_headers)
    assert client.delete(f"{BOOKINGS}/{booking_id}", headers=student_headers).status_code == 409


def test_cannot_cancel_someone_elses_booking(client, seeded, student_headers, other_student_headers):
    booking_id = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    # 404, not 403: the attacker must not even learn that booking exists (IDOR / BOLA).
    assert client.delete(f"{BOOKINGS}/{booking_id}", headers=other_student_headers).status_code == 404
    assert db.session.get(Booking, booking_id).status == "confirmed"


def test_admin_can_cancel_any_booking(client, seeded, student_headers, admin_headers):
    booking_id = _book(client, student_headers, seeded["B-204"]).get_json()["id"]
    assert client.delete(f"{BOOKINGS}/{booking_id}", headers=admin_headers).status_code == 200


def test_cancel_unknown_booking(client, student_headers):
    assert client.delete(f"{BOOKINGS}/9999", headers=student_headers).status_code == 404


def test_cannot_cancel_a_booking_that_already_started(client, seeded, student_user, student_headers):
    started = Booking(
        user_id=student_user.id,
        room_id=seeded["B-204"],
        title="Already running",
        attendees=5,
        start_time=datetime.now() - timedelta(minutes=30),
        end_time=datetime.now() + timedelta(minutes=30),
    )
    db.session.add(started)
    db.session.commit()
    assert client.delete(f"{BOOKINGS}/{started.id}", headers=student_headers).status_code == 409
