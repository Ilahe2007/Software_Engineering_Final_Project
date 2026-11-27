"""Unit tests for the Chain of Responsibility and the booking transaction, without HTTP."""
from datetime import datetime
from types import SimpleNamespace

import pytest
from werkzeug.exceptions import Conflict

from app.bookings.checks import (
    BookingCheck,
    BookingRequest,
    CapacityCheck,
    OverlapCheck,
    TimeRangeCheck,
    build_booking_chain,
)
from app.bookings.service import BookingService
from app.errors import ValidationError

NOW = datetime(2030, 12, 1, 9, 0)


def _room(capacity=30, room_type="lab", equipment=("projector",)):
    return SimpleNamespace(
        id=1,
        code="B-204",
        capacity=capacity,
        is_active=True,
        room_type=SimpleNamespace(name=room_type),
        equipment=[SimpleNamespace(name=name) for name in equipment],
    )


def _request(room=None, start="2030-12-02T10:00", end="2030-12-02T12:00", attendees=20, **extra):
    return BookingRequest(
        room=room or _room(),
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        attendees=attendees,
        **extra,
    )


class FakeBookings:
    """Stands in for BookingRepository and records the order of the calls."""

    def __init__(self, room=None, overlapping=()):
        self.room = room
        self.overlapping = list(overlapping)
        self.calls = []

    def lock_room(self, room_id):
        self.calls.append("lock_room")
        return self.room

    def find_overlapping(self, room_id, start, end):
        self.calls.append("find_overlapping")
        return self.overlapping

    def add(self, booking):
        self.calls.append("add")
        booking.id = 1
        return booking

    def rollback(self):
        self.calls.append("rollback")


def test_set_next_returns_the_next_link_so_calls_can_be_chained():
    first, second, third = BookingCheck(), CapacityCheck(), CapacityCheck()
    assert first.set_next(second).set_next(third) is third


def test_the_chain_stops_at_the_first_failing_link():
    bookings = FakeBookings(overlapping=["clash"])
    chain = TimeRangeCheck(8, 20, now=lambda: NOW)
    chain.set_next(CapacityCheck()).set_next(OverlapCheck(bookings))

    with pytest.raises(ValidationError) as error:
        chain.handle(_request(attendees=500))
    assert "attendees" in error.value.errors
    # The capacity link failed, so the overlap link never queried the database.
    assert bookings.calls == []


def test_checks_run_in_the_documented_order():
    # Everything is wrong at once: the time range is reported because it comes first.
    chain = build_booking_chain(FakeBookings(overlapping=["clash"]), 8, 20)
    with pytest.raises(ValidationError) as error:
        chain.handle(_request(start="2030-12-02T12:00", end="2030-12-02T10:00", attendees=500,
                              required_room_type="lecture_hall"))
    assert set(error.value.errors) == {"end"}


def test_a_suitable_free_room_passes_the_whole_chain():
    bookings = FakeBookings()
    build_booking_chain(bookings, 8, 20).handle(_request(required_room_type="lab",
                                                         required_equipment=frozenset({"projector"})))
    assert bookings.calls == ["find_overlapping"]


def test_overlap_link_raises_conflict():
    clash = SimpleNamespace(start_time=datetime(2030, 12, 2, 9), end_time=datetime(2030, 12, 2, 11))
    with pytest.raises(Conflict, match="09:00 to 11:00"):
        OverlapCheck(FakeBookings(overlapping=[clash])).handle(_request())


def test_time_range_uses_the_injected_clock():
    check = TimeRangeCheck(8, 20, now=lambda: datetime(2030, 12, 2, 11, 0))
    with pytest.raises(ValidationError, match="Invalid request data"):
        check.handle(_request(start="2030-12-02T10:00", end="2030-12-02T12:00"))


def _data(**overrides):
    data = {
        "room_id": 1,
        "title": "Meeting",
        "start": datetime(2030, 12, 2, 10),
        "end": datetime(2030, 12, 2, 12),
        "attendees": 10,
        "room_type": None,
        "equipment": frozenset(),
    }
    data.update(overrides)
    return data


def test_room_is_locked_before_the_overlap_check(app):
    bookings = FakeBookings(room=_room())
    BookingService(8, 20, bookings=bookings).create(SimpleNamespace(id=7), _data())
    # Lock first, then check, then save: the order that prevents double booking.
    assert bookings.calls == ["lock_room", "find_overlapping", "add"]


def test_a_refused_booking_releases_the_lock(app):
    bookings = FakeBookings(room=_room(capacity=5))
    with pytest.raises(ValidationError):
        BookingService(8, 20, bookings=bookings).create(SimpleNamespace(id=7), _data(attendees=10))
    assert bookings.calls == ["lock_room", "rollback"]
