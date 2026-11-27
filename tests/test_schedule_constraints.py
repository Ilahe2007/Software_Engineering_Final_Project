from datetime import datetime, timezone

import pytest

from app.ScheduleEngine.constraints import (
    CapacityConstraint,
    EquipmentConstraint,
    RoomOccupancyConstraint,
    RoomTypeConstraint,
    TimeInterval,
)


@pytest.mark.parametrize(
    ("room_capacity", "expected_attendance", "allowed"),
    [(31, 30, True), (30, 30, True), (29, 30, False)],
)
def test_capacity_constraint(room_capacity, expected_attendance, allowed):
    assert CapacityConstraint.allows(
        room_capacity=room_capacity,
        expected_attendance=expected_attendance,
    ) is allowed


def test_room_type_constraint_accepts_matching_type():
    assert RoomTypeConstraint.allows(room_type="lab", required_room_type="lab")


def test_room_type_constraint_rejects_different_type():
    assert not RoomTypeConstraint.allows(room_type="lecture_hall", required_room_type="lab")


def test_room_type_constraint_accepts_any_type_when_unspecified():
    assert RoomTypeConstraint.allows(room_type="lecture_hall")


def test_equipment_constraint_accepts_all_required_equipment_with_extras():
    assert EquipmentConstraint.allows(
        room_equipment={"computers", "projector", "whiteboard"},
        required_equipment={"computers", "projector"},
    )


def test_equipment_constraint_rejects_room_missing_one_required_item():
    assert not EquipmentConstraint.allows(
        room_equipment={"projector", "whiteboard"},
        required_equipment={"computers", "projector"},
    )


def test_equipment_constraint_accepts_empty_room_when_equipment_is_optional():
    assert EquipmentConstraint.allows(room_equipment=set())


def test_equipment_constraint_rejects_empty_room_when_equipment_is_required():
    assert not EquipmentConstraint.allows(room_equipment=set(), required_equipment={"projector"})


def _interval(start_hour, end_hour):
    return TimeInterval(datetime(2026, 12, 1, start_hour), datetime(2026, 12, 1, end_hour))


@pytest.mark.parametrize(
    ("block_start", "block_end", "allowed"),
    [
        (8, 9, True),
        (9, 10, True),
        (14, 15, True),
        (9, 11, False),
        (13, 15, False),
        (11, 12, False),
        (9, 15, False),
        (10, 14, False),
    ],
    ids=[
        "disjoint", "adjacent-before", "adjacent-after", "overlaps-start", "overlaps-end",
        "block-inside-activity", "activity-inside-block", "identical",
    ],
)
def test_room_occupancy_checks_blocked_intervals(block_start, block_end, allowed):
    assert RoomOccupancyConstraint.allows(
        room_id=1,
        activity_interval=_interval(10, 14),
        blocked_by_room={1: [_interval(block_start, block_end)]},
    ) is allowed


def test_room_occupancy_allows_room_with_no_blocks():
    assert RoomOccupancyConstraint.allows(room_id=1, activity_interval=_interval(10, 11), blocked_by_room={})


def test_room_occupancy_allows_simultaneous_use_of_different_rooms():
    interval = _interval(10, 11)
    assert RoomOccupancyConstraint.allows(room_id=2, activity_interval=interval, blocked_by_room={1: [interval]})


def test_room_occupancy_checks_past_the_first_block():
    assert not RoomOccupancyConstraint.allows(
        room_id=1,
        activity_interval=_interval(10, 12),
        blocked_by_room={1: [_interval(8, 9), _interval(11, 13)]},
    )


def test_room_occupancy_detects_a_block_crossing_midnight():
    block = TimeInterval(datetime(2026, 11, 30, 23), datetime(2026, 12, 1, 2))
    assert not RoomOccupancyConstraint.allows(
        room_id=1,
        activity_interval=_interval(1, 3),
        blocked_by_room={1: [block]},
    )


@pytest.mark.parametrize("end_hour", [9, 10], ids=["reversed", "empty"])
def test_time_interval_rejects_end_at_or_before_start(end_hour):
    with pytest.raises(ValueError, match="start must be before"):
        _interval(10, end_hour)


@pytest.mark.parametrize(
    ("start_zone", "end_zone"),
    [(timezone.utc, None), (None, timezone.utc), (timezone.utc, timezone.utc)],
    ids=["aware-start", "aware-end", "both-aware"],
)
def test_time_interval_rejects_timezone_aware_endpoints(start_zone, end_zone):
    with pytest.raises(ValueError, match="without a timezone"):
        TimeInterval(datetime(2026, 12, 1, 10, tzinfo=start_zone), datetime(2026, 12, 1, 11, tzinfo=end_zone))
