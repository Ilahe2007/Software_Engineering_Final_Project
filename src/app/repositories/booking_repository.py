"""All database access for bookings."""
from ..extensions import db
from ..models import Booking, Room


class BookingRepository:
    def get(self, booking_id):
        return db.session.get(Booking, booking_id)

    def list_for_user(self, user_id, status=None):
        query = db.select(Booking).where(Booking.user_id == user_id).order_by(Booking.start_time)
        if status:
            query = query.where(Booking.status == status)
        return list(db.session.scalars(query))

    def lock_room(self, room_id):
        """Load the room and lock its row until the transaction ends (commit or rollback).

        On PostgreSQL, SELECT ... FOR UPDATE makes a second booking request for the
        same room wait here until the first one is committed. Its overlap check then
        sees the first booking, so two people cannot book the same slot at once.
        SQLite (local development and tests) ignores FOR UPDATE.
        """
        return db.session.scalar(db.select(Room).where(Room.id == room_id).with_for_update())

    def find_overlapping(self, room_id, start, end):
        """Confirmed bookings of this room that share at least one minute with [start, end)."""
        query = (
            db.select(Booking)
            .where(
                Booking.room_id == room_id,
                Booking.status == "confirmed",
                Booking.start_time < end,
                Booking.end_time > start,
            )
            .order_by(Booking.start_time)
        )
        return list(db.session.scalars(query))

    def add(self, booking):
        db.session.add(booking)
        db.session.commit()
        return booking

    def save(self):
        db.session.commit()

    def rollback(self):
        """End the transaction without saving. Releases the room lock taken by lock_room()."""
        db.session.rollback()
