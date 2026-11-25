"""Every error leaves the API as JSON, never as an HTML page."""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ValidationError(Exception):
    """Raised when request data is invalid. `errors` maps field name -> message."""

    def __init__(self, errors):
        super().__init__("Invalid request data")
        self.errors = errors


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify(error="Bad Request", details=err.errors), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return jsonify(error=err.name, message=err.description), err.code
