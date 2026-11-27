"""The checks a booking must pass before it is saved.

Design pattern: Chain of Responsibility. Each rule is one small class (a link).
A link either rejects the booking by raising, or hands it to the next link:

    time range -> capacity -> room type -> equipment -> overlap

The order matters: cheap checks that need no database come first, and the
overlap check, which queries other bookings, runs last. A new rule is a new
class added to build_booking_chain(); no other code changes.

Capacity, room type and equipment reuse Part D's Schedule Engine constraints,
so a booking and the academic schedule follow exactly the same rules.
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from werkzeug.exceptions import Conflict

from ..errors import ValidationError
from ..ScheduleEngine.constraints import CapacityConstraint, EquipmentConstraint, RoomTypeConstraint


@dataclass(frozen=True)
class BookingRequest:
    room: object  # app.models.Room
    start: datetime
    end: datetime
    attendees: int
    required_room_type: str | None = None
    required_equipment: frozenset = frozenset()


class BookingCheck:
    """One link of the chain."""

    def __init__(self):
        self._next = None

    def set_next(self, check):
        """Attach the next link and return it, so links can be chained: a.set_next(b).set_next(c)."""
        self._next = check
        return check

    def handle(self, request):
        self.check(request)
        if self._next is not None:
            self._next.handle(request)

    def check(self, request):
        raise NotImplementedError


class TimeRangeCheck(BookingCheck):
    """Start before end, in the future, on one day, inside the opening hours."""

    def __init__(self, opening_hour, closing_hour, now=datetime.now):
        super().__init__()
        self._opening_hour = opening_hour
        self._closing_hour = closing_hour
        self._now = now

    def check(self, request):
        if request.end <= request.start:
            raise ValidationError({"end": "must be after start"})
        if request.start < self._now():
            raise ValidationError({"start": "must be in the future"})
        if request.start.date() != request.end.date():
            raise ValidationError({"end": "must be on the same day as start"})

        midnight = datetime.combine(request.start.date(), time())
        opening = midnight + timedelta(hours=self._opening_hour)
        closing = midnight + timedelta(hours=self._closing_hour)
        if request.start < opening or request.end > closing:
            raise ValidationError({
                "start": f"rooms can be booked between {self._opening_hour:02d}:00 and {self._closing_hour:02d}:00",
            })


class CapacityCheck(BookingCheck):
    def check(self, request):
        if not CapacityConstraint.allows(room_capacity=request.room.capacity, expected_attendance=request.attendees):
            raise ValidationError({
                "attendees": f"room {request.room.code} has only {request.room.capacity} seats",
            })


class RoomTypeCheck(BookingCheck):
    def check(self, request):
        room_type = request.room.room_type.name
        if not RoomTypeConstraint.allows(room_type=room_type, required_room_type=request.required_room_type):
            raise ValidationError({
                "room_type": f"room {request.room.code} is a {room_type}, not a {request.required_room_type}",
            })


class EquipmentCheck(BookingCheck):
    def check(self, request):
        available = {item.name for item in request.room.equipment}
        if not EquipmentConstraint.allows(room_equipment=available, required_equipment=request.required_equipment):
            missing = ", ".join(sorted(request.required_equipment - available))
            raise ValidationError({"equipment": f"room {request.room.code} has no {missing}"})


class OverlapCheck(BookingCheck):
    """No other confirmed booking of the same room may share a minute with this one.

    Must run inside the transaction that locked the room (BookingRepository.lock_room),
    otherwise two requests could both pass it before either is saved.
    """

    def __init__(self, bookings):
        super().__init__()
        self._bookings = bookings

    def check(self, request):
        clashes = self._bookings.find_overlapping(request.room.id, request.start, request.end)
        if clashes:
            other = clashes[0]
            raise Conflict(
                f"Room {request.room.code} is already booked on {other.start_time:%Y-%m-%d} "
                f"from {other.start_time:%H:%M} to {other.end_time:%H:%M}."
            )


def build_booking_chain(bookings, opening_hour, closing_hour):
    first = TimeRangeCheck(opening_hour, closing_hour)
    (
        first.set_next(CapacityCheck())
        .set_next(RoomTypeCheck())
        .set_next(EquipmentCheck())
        .set_next(OverlapCheck(bookings))
    )
    return first
