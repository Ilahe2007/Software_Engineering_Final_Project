from flask import Blueprint

bp = Blueprint("rooms", __name__)

from . import routes  # noqa: E402,F401
