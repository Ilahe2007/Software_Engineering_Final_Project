"""Users who can log in, and their role."""
from datetime import datetime

from ..extensions import db

ROLES = ("student", "teacher", "admin")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Always stored in lower case, so "Ali@ufaz.az" and "ali@ufaz.az" are the same account.
    email = db.Column(db.String(254), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    # Only a salted hash is stored (werkzeug, scrypt). The password itself never reaches the database.
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # Brute-force protection: after too many wrong passwords the account is locked for a while.
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)

    # Every login token carries this number. Raising it (logout, role change) makes all older tokens invalid.
    token_version = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    __table_args__ = (db.CheckConstraint(f"role IN {ROLES}", name="ck_users_role"),)

    def to_dict(self):
        # Never add password_hash, failed_login_count or token_version here: this goes to the client.
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(timespec="minutes") if self.created_at else None,
        }
