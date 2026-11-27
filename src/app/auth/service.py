"""Registration, login with brute-force protection, logout and role changes."""
from datetime import datetime, timedelta

from flask import current_app
from werkzeug.exceptions import Conflict, NotFound, TooManyRequests, Unauthorized
from werkzeug.security import check_password_hash, generate_password_hash

from ..models import User
from ..repositories import UserRepository

# The same message for "no such email" and "wrong password", so the login form
# cannot be used to find out which emails have an account.
LOGIN_FAILED = "Invalid email or password."
ACCOUNT_LOCKED = "Too many failed logins. Try again later."

# Checked when the email is unknown, so that answer takes as long as a real
# password check. Otherwise response times would reveal which emails exist.
_DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password-only-for-timing")


class AuthService:
    def __init__(self, users=None):
        self._users = users or UserRepository()

    def register(self, email, password, full_name, role="student"):
        """New accounts are always students unless an admin creates them (see cli.py)."""
        if self._users.get_by_email(email):
            raise Conflict("An account with this email already exists.")
        user = User(
            email=email,
            full_name=full_name,
            password_hash=generate_password_hash(password),
            role=role,
        )
        return self._users.add(user)

    def authenticate(self, email, password, max_failed, lockout_minutes):
        user = self._users.get_by_email(email)
        now = datetime.now()

        if user is None:
            check_password_hash(_DUMMY_PASSWORD_HASH, password)
            raise Unauthorized(LOGIN_FAILED)

        # Checked before the password, so a locked account cannot keep being guessed.
        if user.locked_until and user.locked_until > now:
            raise TooManyRequests(ACCOUNT_LOCKED)

        if not check_password_hash(user.password_hash, password):
            self._record_failure(user, now, max_failed, lockout_minutes)
            raise Unauthorized(LOGIN_FAILED)

        if not user.is_active:
            current_app.logger.warning("Login refused: user_id=%s is deactivated", user.id)
            raise Unauthorized(LOGIN_FAILED)

        user.failed_login_count = 0
        user.locked_until = None
        self._users.save()
        current_app.logger.info("Login succeeded: user_id=%s", user.id)
        return user

    def _record_failure(self, user, now, max_failed, lockout_minutes):
        user.failed_login_count += 1
        current_app.logger.warning(
            "Login failed: user_id=%s attempt=%s", user.id, user.failed_login_count
        )
        if user.failed_login_count >= max_failed:
            user.locked_until = now + timedelta(minutes=lockout_minutes)
            user.failed_login_count = 0
            current_app.logger.warning(
                "Account locked: user_id=%s until=%s", user.id, user.locked_until.isoformat(timespec="minutes")
            )
        self._users.save()

    def logout(self, user):
        # Tokens are not stored, so they cannot be deleted. Raising the version
        # makes every token issued before now invalid, on every device.
        user.token_version += 1
        self._users.save()

    def change_role(self, admin, user_id, role):
        if user_id == admin.id:
            # Stops the last admin from locking everyone out of the admin panel by accident.
            raise Conflict("You cannot change your own role.")
        user = self._users.get(user_id)
        if user is None:
            raise NotFound(f"User {user_id} not found.")
        old_role = user.role
        user.role = role
        # The user's old tokens stop working, so the new role applies from their next login.
        user.token_version += 1
        self._users.save()
        current_app.logger.warning(
            "Role changed: user_id=%s %s -> %s by admin_id=%s", user.id, old_role, role, admin.id
        )
        return user
