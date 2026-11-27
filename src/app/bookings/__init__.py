"""Room bookings for events. Owned by Part B."""
from flask import Blueprint

bp = Blueprint("bookings", __name__)

from . import routes  # noqa: E402,F401
