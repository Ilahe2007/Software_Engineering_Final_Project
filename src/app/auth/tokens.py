"""Login tokens: JSON Web Tokens signed with HS256 and the app's SECRET_KEY.

A token only says WHO the user is (`sub`) and which token generation it belongs
to (`ver`). The role is deliberately not in the token: it is read from the
database on every request, so a role change or a ban applies at once.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sub", "ver", "iat", "exp"]


def create_access_token(user, secret, minutes):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "ver": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token, secret):
    """Return the token's claims, or None if it is forged, expired or malformed."""
    try:
        # `algorithms` is a fixed list, so a token that says "alg": "none" (no signature)
        # or names another algorithm is refused instead of being trusted.
        claims = jwt.decode(token, secret, algorithms=[ALGORITHM], options={"require": REQUIRED_CLAIMS})
    except jwt.InvalidTokenError:
        return None
    if not str(claims["sub"]).isdigit() or not isinstance(claims["ver"], int):
        return None
    return claims
