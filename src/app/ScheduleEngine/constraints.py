"""Check room suitability and availability for an activity."""

from collections.abc import Collection, Mapping, Set
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar


RoomId = TypeVar("RoomId")


class CapacityConstraint:
    """A room must have a seat for every expected attendee."""

    @staticmethod
    def allows(*, room_capacity: int, expected_attendance: int) -> bool:
        return room_capacity >= expected_attendance


class RoomTypeConstraint:
    """A specified room type must match the candidate room's type."""

    @staticmethod
    def allows(*, room_type: str, required_room_type: str | None = None) -> bool:
        return required_room_type is None or room_type == required_room_type


class EquipmentConstraint:
    """A room must provide every required piece of equipment."""

    @staticmethod
    def allows(*, room_equipment: Set[str], required_equipment: Set[str] = frozenset()) -> bool:
        return required_equipment <= room_equipment


@dataclass(frozen=True)
class TimeInterval:
    """An interval in local university time, with the end excluded."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is not None or self.end.tzinfo is not None:
            raise ValueError("Interval times must use local university time without a timezone.")
        if self.start >= self.end:
            raise ValueError("Interval start must be before its end.")

    def overlaps(self, other: "TimeInterval") -> bool:
        return self.start < other.end and other.start < self.end


class RoomOccupancyConstraint:
    """A candidate room must be free for the entire activity interval."""

    @staticmethod
    def allows(
        *,
        room_id: RoomId,
        activity_interval: TimeInterval,
        blocked_by_room: Mapping[RoomId, Collection[TimeInterval]],
    ) -> bool:
        return not any(activity_interval.overlaps(block) for block in blocked_by_room.get(room_id, ()))
