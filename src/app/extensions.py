"""Flask extensions are created here without an app, then bound in create_app().

This avoids circular imports: models import `db` from here, not from the app.
"""
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
swagger = Swagger()
