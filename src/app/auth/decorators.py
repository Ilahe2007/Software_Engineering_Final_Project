"""Login and role checks for view functions.

Design pattern: Decorator. @login_required and @role_required("admin") wrap a
view and add the security check around it, so the view itself only contains
its own logic:

    @bp.post("/rooms")
    @role_required("admin")
    def create_room(): ...

The client sends `Authorization: Bearer <token>` (from POST /api/v1/auth/login).
The logged-in user is available in the view as current_user().
"""
from functools import wraps

from flask import abort, current_app, g, request

from ..repositories import UserRepository
from .tokens import decode_access_token

INVALID_TOKEN = "Invalid or expired token. Log in again."

users = UserRepository()


def _user_from_token():
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        abort(401, "Log in first and send the header 'Authorization: Bearer <token>'.")

    claims = decode_access_token(token.strip(), current_app.config["SECRET_KEY"])
    if claims is None:
        abort(401, INVALID_TOKEN)

    user = users.get(int(claims["sub"]))
    # A token is refused if its user was deleted or deactivated, or if it was
    # issued before a logout or role change (token_version went up since then).
    if user is None or not user.is_active or claims["ver"] != user.token_version:
        abort(401, INVALID_TOKEN)
    return user


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _user_from_token()
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """Allow only users whose role is one of `roles`. Implies @login_required."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = _user_from_token()
            if user.role not in roles:
                current_app.logger.warning(
                    "Access denied: user_id=%s role=%s %s %s", user.id, user.role, request.method, request.path
                )
                abort(403, f"This action needs one of these roles: {', '.join(roles)}.")
            g.current_user = user
            return view(*args, **kwargs)

        return wrapper

    return decorator


def current_user():
    """The user of the current request. Only call it inside a view protected by one of the decorators above."""
    return g.current_user
