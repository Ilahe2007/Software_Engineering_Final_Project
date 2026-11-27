"""Repository pattern: every database query lives in a repository class.

RoomRepository was started in Part A because the room endpoints need it.
Part C owns this package and adds BookingRepository, ActivityRepository, etc.
"""
from .room_repository import RoomRepository

__all__ = ["RoomRepository"]
