"""A room booked by a user for an event."""
from datetime import datetime

from ..extensions import db

BOOKING_STATUSES = ("confirmed", "cancelled")


def _iso(value):
    return value.isoformat(timespec="minutes") if value else None


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    attendees = db.Column(db.Integer, nullable=False)
    # Local university time without a timezone. The range includes start and excludes end.
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # Bookings are cancelled, not deleted, so the history and the audit log stay complete.
    status = db.Column(db.String(20), nullable=False, default="confirmed")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    cancelled_at = db.Column(db.DateTime)

    user = db.relationship("User")
    room = db.relationship("Room")

    __table_args__ = (
        db.CheckConstraint("end_time > start_time", name="ck_bookings_time_range"),
        db.CheckConstraint(f"status IN {BOOKING_STATUSES}", name="ck_bookings_status"),
        db.Index("ix_bookings_room_time", "room_id", "start_time"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "room_id": self.room_id,
            "room_code": self.room.code if self.room else None,
            "title": self.title,
            "attendees": self.attendees,
            "start": _iso(self.start_time),
            "end": _iso(self.end_time),
            "status": self.status,
            "created_at": _iso(self.created_at),
            "cancelled_at": _iso(self.cancelled_at),
        }
