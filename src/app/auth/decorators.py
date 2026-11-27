"""TEMPORARY role check so Part A's admin endpoints can be built and tested.

Part B replaces the body of role_required() with real login (session or JWT)
and adds login_required(). The name and signature stay the same, so no other
file has to change.

Until then: in development and testing, send the header `X-User-Role: admin`.
In production this stub refuses every request, so nothing is ever left open.
"""
from functools import wraps

from flask import abort, current_app, request


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_app.config.get("ALLOW_DEV_AUTH"):
                abort(501, "Login is not implemented yet (Part B).")
            role = request.headers.get("X-User-Role")
            if role is None:
                abort(401, "Missing X-User-Role header.")
            if role not in roles:
                abort(403, f"This action needs one of these roles: {', '.join(roles)}.")
            return view(*args, **kwargs)

        return wrapper

    return decorator
