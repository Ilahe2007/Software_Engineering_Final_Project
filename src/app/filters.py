"""Reads the room filters from the query string. Shared by /rooms and /availability."""
from .errors import ValidationError


def parse_room_filters(args):
    """?building=B&min_capacity=30&room_type=lab&equipment=projector,computers"""
    filters = {
        "building": (args.get("building") or "").strip() or None,
        "room_type": (args.get("room_type") or "").strip() or None,
        "min_capacity": None,
        "equipment": [],
    }

    raw_capacity = args.get("min_capacity")
    if raw_capacity:
        try:
            filters["min_capacity"] = int(raw_capacity)
        except ValueError:
            raise ValidationError({"min_capacity": "must be a whole number"})

    raw_equipment = args.get("equipment")
    if raw_equipment:
        filters["equipment"] = [item.strip() for item in raw_equipment.split(",") if item.strip()]

    return filters
