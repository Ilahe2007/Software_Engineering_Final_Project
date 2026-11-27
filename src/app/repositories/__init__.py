"""Repository pattern: every database query lives in a repository class.

RoomRepository was started in Part A because the room endpoints need it.
UserRepository and BookingRepository were started in Part B for login and booking.
Part C owns this package and adds ActivityRepository, etc.
"""
from .booking_repository import BookingRepository
from .room_repository import RoomRepository
from .user_repository import UserRepository

__all__ = ["BookingRepository", "RoomRepository", "UserRepository"]
