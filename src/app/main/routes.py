from flask import jsonify
from sqlalchemy import text

from ..extensions import db
from . import bp


@bp.get("/")
def index():
    """API entry point.
    ---
    tags: [Health]
    responses:
      200:
        description: Name of the API and where the docs are.
    """
    return jsonify(name="University Room Management API", docs="/docs/", health="/health")


@bp.get("/health")
def health():
    """Health check used by Render and UptimeRobot (PW7, PW8).
    ---
    tags: [Health]
    responses:
      200:
        description: The app and its database are working.
      503:
        description: The database cannot be reached.
    """
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify(status="error", database="unreachable"), 503
    return jsonify(status="ok", database="ok")
