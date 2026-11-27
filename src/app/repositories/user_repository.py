"""All database access for users."""
from ..extensions import db
from ..models import User


class UserRepository:
    def get(self, user_id):
        return db.session.get(User, user_id)

    def get_by_email(self, email):
        return db.session.scalar(db.select(User).where(User.email == email.lower()))

    def add(self, user):
        db.session.add(user)
        db.session.commit()
        return user

    def save(self):
        db.session.commit()
