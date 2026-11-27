"""HTTP security headers added to every response."""
from flask import request

API_PREFIX = "/api/"


def register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        headers = response.headers
        # The browser must not guess a different content type (e.g. run JSON as a script).
        headers.setdefault("X-Content-Type-Options", "nosniff")
        # No other site may show our pages in a frame (clickjacking).
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")

        if request.path.startswith(API_PREFIX):
            # API answers are JSON only: nothing in them may be loaded or run as a page.
            # Not applied to /docs/, because Swagger UI needs its scripts and styles.
            headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            # Tokens and personal bookings must not stay in browser or proxy caches.
            headers.setdefault("Cache-Control", "no-store")

        if not app.debug and not app.testing:
            # Production runs behind HTTPS (Render). Browsers then refuse plain HTTP for a year.
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
