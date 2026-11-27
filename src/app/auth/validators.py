"""Checks the JSON body of auth requests and returns clean values."""
import re

from ..errors import ValidationError
from ..models import ROLES

REGISTER_FIELDS = {"email", "password", "full_name"}
LOGIN_FIELDS = {"email", "password"}

# Long enough to resist guessing (NIST SP 800-63B asks for at least 8).
MIN_PASSWORD_LENGTH = 10
# An upper limit, so nobody can make the server hash a 10 MB "password".
MAX_PASSWORD_LENGTH = 128
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# The most common passwords that still pass the length rule. They are the first ones an attacker tries.
COMMON_PASSWORDS = {
    "1234567890",
    "12345678910",
    "1q2w3e4r5t",
    "abc1234567",
    "admin12345",
    "iloveyou12",
    "letmein123",
    "passw0rd123",
    "password1!",
    "password12",
    "password123",
    "password1234",
    "qwerty1234",
    "qwertyuiop",
    "welcome123",
}


def _require_object(data, allowed):
    if not isinstance(data, dict):
        raise ValidationError({"body": "must be a JSON object"})
    errors = {}
    # Refusing unknown fields stops mass assignment: a client cannot sneak in
    # {"role": "admin"} or {"is_active": true} and have it saved.
    unknown = set(data) - allowed
    if unknown:
        errors["unknown_fields"] = f"not allowed: {', '.join(sorted(unknown))}"
    return errors


def _clean_email(value, errors):
    if not isinstance(value, str) or not value.strip():
        errors["email"] = "is required"
        return None
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        errors["email"] = "must be a valid email address"
        return None
    return email


def _check_password_strength(password, email, errors):
    if not isinstance(password, str) or not password:
        errors["password"] = "is required"
    elif len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = f"must be at least {MIN_PASSWORD_LENGTH} characters"
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = f"must be at most {MAX_PASSWORD_LENGTH} characters"
    elif password.lower() in COMMON_PASSWORDS:
        errors["password"] = "is too common, choose another one"
    elif email and password.lower() == email:
        errors["password"] = "must not be your email address"


def validate_registration(data):
    """Returns {"email", "password", "full_name"}. Raises ValidationError listing every problem."""
    errors = _require_object(data, REGISTER_FIELDS)
    email = _clean_email(data.get("email"), errors)

    full_name = data.get("full_name")
    if not isinstance(full_name, str) or not full_name.strip():
        errors["full_name"] = "is required"
    elif len(full_name.strip()) > 100:
        errors["full_name"] = "must be at most 100 characters"

    password = data.get("password")
    _check_password_strength(password, email, errors)

    if errors:
        raise ValidationError(errors)
    return {"email": email, "password": password, "full_name": full_name.strip()}


def validate_login(data):
    """Only checks the shape. The strength rules are not applied here, so they never reveal anything."""
    errors = _require_object(data, LOGIN_FIELDS)
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not email.strip():
        errors["email"] = "is required"
    if not isinstance(password, str) or not password:
        errors["password"] = "is required"
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = f"must be at most {MAX_PASSWORD_LENGTH} characters"
    if errors:
        raise ValidationError(errors)
    return email.strip().lower(), password


def validate_role_change(data):
    errors = _require_object(data, {"role"})
    role = data.get("role")
    if role not in ROLES:
        errors["role"] = f"must be one of: {', '.join(ROLES)}"
    if errors:
        raise ValidationError(errors)
    return role
