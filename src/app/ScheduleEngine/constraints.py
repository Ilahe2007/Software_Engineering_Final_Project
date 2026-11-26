"""Check whether a room meets an activity's requirements."""

from collections.abc import Set


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
