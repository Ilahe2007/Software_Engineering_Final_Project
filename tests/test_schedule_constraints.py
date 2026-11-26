import pytest

from app.ScheduleEngine.constraints import CapacityConstraint, EquipmentConstraint, RoomTypeConstraint


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
