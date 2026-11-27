"""Checks the JSON body and query string of booking requests and returns clean values.

These checks are about the shape of the data (types, formats). Whether the room
is actually suitable and free is decided later by the chain in checks.py.
"""
from datetime import datetime

from ..errors import ValidationError
from ..models import BOOKING_STATUSES

BOOKING_FIELDS = {"room_id", "title", "start", "end", "attendees", "room_type", "equipment"}
REQUIRED_FIELDS = {"room_id", "title", "start", "end", "attendees"}
MAX_TITLE_LENGTH = 120


def _positive_int(value):
    # bool is a subclass of int in Python, so reject it explicitly.
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _parse_local_time(value, field, errors):
    if not isinstance(value, str):
        errors[field] = "must be a date and time like 2026-12-01T10:00"
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors[field] = "must be a date and time like 2026-12-01T10:00"
        return None
    if parsed.tzinfo is not None:
        errors[field] = "must be local university time without a timezone"
        return None
    return parsed.replace(second=0, microsecond=0)


def validate_booking_payload(data):
    """Returns the clean booking fields. Raises ValidationError listing every problem at once."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    # Refusing unknown fields stops mass assignment: a client cannot set
    # user_id (book in someone else's name) or status by adding them to the body.
    unknown = set(data) - BOOKING_FIELDS
    if unknown:
        errors["unknown_fields"] = f"not allowed: {', '.join(sorted(unknown))}"
    for field in sorted(REQUIRED_FIELDS - set(data)):
        errors[field] = "is required"

    clean = {"room_type": None, "equipment": frozenset()}

    if "room_id" in data:
        if _positive_int(data["room_id"]):
            clean["room_id"] = data["room_id"]
        else:
            errors["room_id"] = "must be a room id (a whole number)"

    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not title.strip():
            errors["title"] = "must be a non-empty string"
        elif len(title.strip()) > MAX_TITLE_LENGTH:
            errors["title"] = f"must be at most {MAX_TITLE_LENGTH} characters"
        else:
            clean["title"] = title.strip()

    if "attendees" in data:
        if _positive_int(data["attendees"]):
            clean["attendees"] = data["attendees"]
        else:
            errors["attendees"] = "must be a whole number of at least 1"

    for field in ("start", "end"):
        if field in data:
            clean[field] = _parse_local_time(data[field], field, errors)

    if data.get("room_type") is not None:
        if isinstance(data["room_type"], str) and data["room_type"].strip():
            clean["room_type"] = data["room_type"].strip()
        else:
            errors["room_type"] = "must be a room type name"

    if "equipment" in data:
        items = data["equipment"]
        if isinstance(items, list) and all(isinstance(item, str) and item.strip() for item in items):
            clean["equipment"] = frozenset(item.strip() for item in items)
        else:
            errors["equipment"] = "must be a list of equipment names"

    if errors:
        raise ValidationError(errors)
    return clean


def parse_status_filter(args):
    status = (args.get("status") or "").strip() or None
    if status is not None and status not in BOOKING_STATUSES:
        raise ValidationError({"status": f"must be one of: {', '.join(BOOKING_STATUSES)}"})
    return status
