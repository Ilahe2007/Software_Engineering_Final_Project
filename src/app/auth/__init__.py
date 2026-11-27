"""Authentication and roles. Owned by Part B.

POST /api/v1/auth/register and /login give a signed token (JWT). Every protected
endpoint reads it from the header `Authorization: Bearer <token>` through the
@login_required and @role_required(...) decorators in decorators.py.
"""
from flask import Blueprint

bp = Blueprint("auth", __name__)


def init_app(app):
    """Things that belong to the whole app, not only to the /auth endpoints."""
    from .cli import create_admin_command
    from .security_headers import register_security_headers

    register_security_headers(app)
    app.cli.add_command(create_admin_command)


from . import routes  # noqa: E402,F401
