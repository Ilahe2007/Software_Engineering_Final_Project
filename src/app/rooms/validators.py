"""Checks the JSON body of room requests and returns clean values."""
from ..errors import ValidationError

ROOM_FIELDS = {"code", "name", "building", "floor", "capacity", "room_type", "equipment", "is_active"}
REQUIRED_ON_CREATE = {"code", "building", "capacity", "room_type"}


def _non_empty_string(value, field, errors, max_length):
    if not isinstance(value, str) or not value.strip():
        errors[field] = "must be a non-empty string"
        return None
    value = value.strip()
    if len(value) > max_length:
        errors[field] = f"must be at most {max_length} characters"
        return None
    return value


def validate_room_payload(data, partial=False):
    """Validate a create (partial=False) or update (partial=True) body.

    Returns a dict that only contains the fields that were sent.
    Raises ValidationError listing every problem at once.
    """
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})

    errors = {}
    unknown = set(data) - ROOM_FIELDS
    if unknown:
        errors["unknown_fields"] = f"not allowed: {', '.join(sorted(unknown))}"

    if not partial:
        for field in sorted(REQUIRED_ON_CREATE - set(data)):
            errors[field] = "is required"

    clean = {}
    if "code" in data:
        clean["code"] = _non_empty_string(data["code"], "code", errors, 20)
    if "building" in data:
        clean["building"] = _non_empty_string(data["building"], "building", errors, 50)
    if "room_type" in data:
        clean["room_type"] = _non_empty_string(data["room_type"], "room_type", errors, 50)
    if "name" in data:
        clean["name"] = None if data["name"] is None else _non_empty_string(data["name"], "name", errors, 100)

    if "capacity" in data:
        capacity = data["capacity"]
        # bool is a subclass of int in Python, so reject it explicitly.
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            errors["capacity"] = "must be a whole number of at least 1"
        else:
            clean["capacity"] = capacity

    if "floor" in data:
        floor = data["floor"]
        if floor is not None and (not isinstance(floor, int) or isinstance(floor, bool)):
            errors["floor"] = "must be a whole number or null"
        else:
            clean["floor"] = floor

    if "equipment" in data:
        items = data["equipment"]
        if not isinstance(items, list) or not all(isinstance(i, str) and i.strip() for i in items):
            errors["equipment"] = "must be a list of equipment names"
        else:
            clean["equipment"] = sorted({i.strip() for i in items})

    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            errors["is_active"] = "must be true or false"
        else:
            clean["is_active"] = data["is_active"]

    if errors:
        raise ValidationError(errors)
    return clean


def validate_name_payload(data, max_length=50):
    """For the small 'create room type' and 'create equipment' bodies."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors = {}
    name = _non_empty_string(data.get("name"), "name", errors, max_length)
    description = data.get("description")
    if description is not None and not isinstance(description, str):
        errors["description"] = "must be a string"
    if errors:
        raise ValidationError(errors)
    return name, description


def validate_name_update(data, allow_description=False, max_length=50):
    """For editing a room type or an equipment name. Returns only the fields that were sent."""
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})
    allowed = {"name", "description"} if allow_description else {"name"}
    errors = {}
    clean = {}
    unknown = set(data) - allowed
    if unknown:
        errors["unknown_fields"] = f"not allowed: {', '.join(sorted(unknown))}"
    if "name" in data:
        clean["name"] = _non_empty_string(data["name"], "name", errors, max_length)
    if allow_description and "description" in data:
        if data["description"] is not None and not isinstance(data["description"], str):
            errors["description"] = "must be a string or null"
        else:
            clean["description"] = data["description"]
    if not errors and not clean:
        errors["body"] = f"send at least one of: {', '.join(sorted(allowed))}"
    if errors:
        raise ValidationError(errors)
    return clean
