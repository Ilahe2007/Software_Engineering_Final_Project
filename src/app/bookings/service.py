"""Creating, listing and cancelling bookings."""
from datetime import datetime

from flask import current_app
from werkzeug.exceptions import Conflict, HTTPException, NotFound

from ..errors import ValidationError
from ..models import Booking
from ..repositories import BookingRepository
from .checks import BookingRequest, build_booking_chain


class BookingService:
    def __init__(self, opening_hour, closing_hour, bookings=None):
        self._bookings = bookings or BookingRepository()
        self._chain = build_booking_chain(self._bookings, opening_hour, closing_hour)

    def create(self, user, data):
        """Check and save a booking in ONE transaction, so it cannot race another request.

        1. Lock the room row (PostgreSQL: SELECT ... FOR UPDATE).
        2. Run the chain of checks, including the overlap check.
        3. Save the booking; the commit releases the lock.
        A second request for the same room waits at step 1 and then sees this booking at step 2.
        """
        try:
            room = self._bookings.lock_room(data["room_id"])
            if room is None:
                raise NotFound(f"Room {data['room_id']} not found.")
            if not room.is_active:
                raise ValidationError({"room_id": f"room {room.code} is no longer in use"})
            self._chain.handle(BookingRequest(
                room=room,
                start=data["start"],
                end=data["end"],
                attendees=data["attendees"],
                required_room_type=data["room_type"],
                required_equipment=data["equipment"],
            ))
        except (HTTPException, ValidationError):
            self._bookings.rollback()  # releases the room lock straight away
            raise

        booking = Booking(
            user_id=user.id,
            room_id=room.id,
            title=data["title"],
            attendees=data["attendees"],
            start_time=data["start"],
            end_time=data["end"],
            status="confirmed",
        )
        self._bookings.add(booking)
        current_app.logger.info("Booking created: booking_id=%s user_id=%s room_id=%s", booking.id, user.id, room.id)
        return booking

    def list_for_user(self, user, status=None):
        return self._bookings.list_for_user(user.id, status)

    def cancel(self, user, booking_id):
        booking = self._bookings.get(booking_id)
        # Someone else's booking gets the same 404 as a booking that does not exist.
        # A 403 would confirm that the id exists (OWASP API1: Broken Object Level Authorization).
        if booking is None or (booking.user_id != user.id and user.role != "admin"):
            raise NotFound(f"Booking {booking_id} not found.")
        if booking.status == "cancelled":
            raise Conflict("This booking is already cancelled.")
        if booking.start_time <= datetime.now():
            raise Conflict("A booking that has already started cannot be cancelled.")

        booking.status = "cancelled"
        booking.cancelled_at = datetime.now()
        self._bookings.save()
        current_app.logger.info("Booking cancelled: booking_id=%s by user_id=%s", booking.id, user.id)
        return booking
