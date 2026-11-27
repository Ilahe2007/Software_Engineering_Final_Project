"""Room management: everyone can browse rooms, only admins can change them."""
from flask import abort, jsonify, request

from ..auth.decorators import role_required
from ..errors import ValidationError
from ..filters import parse_room_filters
from ..models import Room
from ..repositories import RoomRepository
from . import bp
from .validators import validate_name_payload, validate_name_update, validate_room_payload

rooms = RoomRepository()


def _resolve_room_type(name):
    room_type = rooms.get_room_type_by_name(name)
    if room_type is None:
        raise ValidationError({"room_type": f"unknown room type '{name}'. Create it first."})
    return room_type


def _resolve_equipment(names):
    found = rooms.get_equipment_by_names(names)
    missing = set(names) - {item.name for item in found}
    if missing:
        raise ValidationError({"equipment": f"unknown equipment: {', '.join(sorted(missing))}"})
    return found


@bp.get("/rooms")
def list_rooms():
    """List rooms, with optional filters.
    ---
    tags: [Rooms]
    parameters:
      - {name: building, in: query, type: string, description: "Exact building name, e.g. B"}
      - {name: min_capacity, in: query, type: integer, description: "Rooms with at least this many seats"}
      - {name: room_type, in: query, type: string, description: "e.g. lecture_hall, lab, classroom"}
      - {name: equipment, in: query, type: string, description: "Comma separated, the room must have all of them, e.g. projector,computers"}
    responses:
      200:
        description: Matching active rooms.
    """
    filters = parse_room_filters(request.args)
    result = rooms.list_rooms(**filters)
    return jsonify(count=len(result), rooms=[room.to_dict() for room in result])


@bp.get("/rooms/<int:room_id>")
def get_room(room_id):
    """Get one room.
    ---
    tags: [Rooms]
    parameters:
      - {name: room_id, in: path, type: integer, required: true}
    responses:
      200: {description: The room.}
      404: {description: No room with this id.}
    """
    room = rooms.get(room_id)
    if room is None:
        abort(404, f"Room {room_id} not found.")
    return jsonify(room.to_dict())


@bp.post("/rooms")
@role_required("admin")
def create_room():
    """Create a room (admin).
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [code, building, capacity, room_type]
          example: {code: "B-204", name: "Computer lab 2", building: "B", floor: 2, capacity: 30, room_type: "lab", equipment: ["computers", "projector"]}
    responses:
      201: {description: Room created.}
      400: {description: Invalid data.}
      409: {description: A room with this code already exists.}
    """
    data = validate_room_payload(request.get_json(silent=True))
    if rooms.get_by_code(data["code"]):
        abort(409, f"Room code '{data['code']}' already exists.")

    room = Room(
        code=data["code"],
        name=data.get("name"),
        building=data["building"],
        floor=data.get("floor"),
        capacity=data["capacity"],
        room_type=_resolve_room_type(data["room_type"]),
        equipment=_resolve_equipment(data.get("equipment", [])),
        is_active=data.get("is_active", True),
    )
    rooms.add(room)
    return jsonify(room.to_dict()), 201


@bp.patch("/rooms/<int:room_id>")
@role_required("admin")
def update_room(room_id):
    """Change some fields of a room (admin).
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: room_id, in: path, type: integer, required: true}
      - in: body
        name: body
        required: true
        schema:
          type: object
          example: {capacity: 40, equipment: ["projector", "whiteboard"]}
    responses:
      200: {description: Room updated.}
      400: {description: Invalid data.}
      404: {description: No room with this id.}
      409: {description: Another room already uses this code.}
    """
    room = rooms.get(room_id)
    if room is None:
        abort(404, f"Room {room_id} not found.")

    data = validate_room_payload(request.get_json(silent=True), partial=True)
    if "code" in data and data["code"] != room.code and rooms.get_by_code(data["code"]):
        abort(409, f"Room code '{data['code']}' already exists.")

    if "room_type" in data:
        room.room_type = _resolve_room_type(data.pop("room_type"))
    if "equipment" in data:
        room.equipment = _resolve_equipment(data.pop("equipment"))
    for field, value in data.items():
        setattr(room, field, value)

    rooms.save()
    return jsonify(room.to_dict())


@bp.delete("/rooms/<int:room_id>")
@role_required("admin")
def deactivate_room(room_id):
    """Deactivate a room (admin). It is hidden from lists but kept for booking history.
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: room_id, in: path, type: integer, required: true}
    responses:
      200: {description: Room deactivated.}
      404: {description: No room with this id.}
    """
    room = rooms.get(room_id)
    if room is None:
        abort(404, f"Room {room_id} not found.")
    room.is_active = False
    rooms.save()
    return jsonify(room.to_dict())


@bp.get("/room-types")
def list_room_types():
    """List room types.
    ---
    tags: [Rooms]
    responses:
      200: {description: All room types.}
    """
    return jsonify([room_type.to_dict() for room_type in rooms.list_room_types()])


@bp.post("/room-types")
@role_required("admin")
def create_room_type():
    """Create a room type (admin).
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name]
          example: {name: "lab", description: "Room with computers"}
    responses:
      201: {description: Room type created.}
      409: {description: Already exists.}
    """
    name, description = validate_name_payload(request.get_json(silent=True))
    if rooms.get_room_type_by_name(name):
        abort(409, f"Room type '{name}' already exists.")
    return jsonify(rooms.add_room_type(name, description).to_dict()), 201


@bp.patch("/room-types/<int:room_type_id>")
@role_required("admin")
def update_room_type(room_type_id):
    """Rename a room type or change its description (admin).
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: room_type_id, in: path, type: integer, required: true}
      - in: body
        name: body
        required: true
        schema:
          type: object
          example: {name: "computer_lab", description: "Room with computers"}
    responses:
      200: {description: Room type updated.}
      400: {description: Invalid data.}
      404: {description: No room type with this id.}
      409: {description: Another room type already has this name.}
    """
    room_type = rooms.get_room_type(room_type_id)
    if room_type is None:
        abort(404, f"Room type {room_type_id} not found.")
    data = validate_name_update(request.get_json(silent=True), allow_description=True)
    if "name" in data and data["name"] != room_type.name and rooms.get_room_type_by_name(data["name"]):
        abort(409, f"Room type '{data['name']}' already exists.")
    for field, value in data.items():
        setattr(room_type, field, value)
    rooms.save()
    return jsonify(room_type.to_dict())


@bp.delete("/room-types/<int:room_type_id>")
@role_required("admin")
def delete_room_type(room_type_id):
    """Delete a room type (admin). Refused while any room still has this type.
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: room_type_id, in: path, type: integer, required: true}
    responses:
      204: {description: Room type deleted.}
      404: {description: No room type with this id.}
      409: {description: Some rooms still use this type.}
    """
    room_type = rooms.get_room_type(room_type_id)
    if room_type is None:
        abort(404, f"Room type {room_type_id} not found.")
    in_use = rooms.count_rooms_with_type(room_type_id)
    if in_use:
        abort(409, f"{in_use} room(s) still have the type '{room_type.name}'. Change them first.")
    rooms.delete(room_type)
    return "", 204


@bp.get("/equipment")
def list_equipment():
    """List equipment names.
    ---
    tags: [Rooms]
    responses:
      200: {description: All equipment.}
    """
    return jsonify([item.to_dict() for item in rooms.list_equipment()])


@bp.post("/equipment")
@role_required("admin")
def create_equipment():
    """Create an equipment name (admin).
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name]
          example: {name: "projector"}
    responses:
      201: {description: Equipment created.}
      409: {description: Already exists.}
    """
    name, _ = validate_name_payload(request.get_json(silent=True))
    if rooms.get_equipment_by_names([name]):
        abort(409, f"Equipment '{name}' already exists.")
    return jsonify(rooms.add_equipment(name).to_dict()), 201


@bp.patch("/equipment/<int:equipment_id>")
@role_required("admin")
def update_equipment(equipment_id):
    """Rename a piece of equipment (admin). Every room that has it shows the new name.
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: equipment_id, in: path, type: integer, required: true}
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [name]
          example: {name: "video_projector"}
    responses:
      200: {description: Equipment renamed.}
      400: {description: Invalid data.}
      404: {description: No equipment with this id.}
      409: {description: Another piece of equipment already has this name.}
    """
    item = rooms.get_equipment(equipment_id)
    if item is None:
        abort(404, f"Equipment {equipment_id} not found.")
    data = validate_name_update(request.get_json(silent=True))
    if data["name"] != item.name and rooms.get_equipment_by_names([data["name"]]):
        abort(409, f"Equipment '{data['name']}' already exists.")
    item.name = data["name"]
    rooms.save()
    return jsonify(item.to_dict())


@bp.delete("/equipment/<int:equipment_id>")
@role_required("admin")
def delete_equipment(equipment_id):
    """Delete a piece of equipment (admin). Refused while any room still has it.
    ---
    tags: [Rooms (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: equipment_id, in: path, type: integer, required: true}
    responses:
      204: {description: Equipment deleted.}
      404: {description: No equipment with this id.}
      409: {description: Some rooms still have this equipment.}
    """
    item = rooms.get_equipment(equipment_id)
    if item is None:
        abort(404, f"Equipment {equipment_id} not found.")
    in_use = rooms.count_rooms_with_equipment(equipment_id)
    if in_use:
        abort(409, f"{in_use} room(s) still have '{item.name}'. Remove it from them first.")
    rooms.delete(item)
    return "", 204
