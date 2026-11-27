"""All SQLAlchemy models. Import them here so db.create_all() sees every table.

Part C owns the data model from here on (migrations, Activity...). User and
Booking were started in Part B because login and booking need them.
"""
from .booking import BOOKING_STATUSES, Booking
from .room import Equipment, Room, RoomType, room_equipment
from .user import ROLES, User

__all__ = [
    "BOOKING_STATUSES",
    "Booking",
    "Equipment",
    "ROLES",
    "Room",
    "RoomType",
    "User",
    "room_equipment",
]
