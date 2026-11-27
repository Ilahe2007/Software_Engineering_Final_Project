"""`flask create-admin`: the only way to create the first administrator.

Registration through the API always gives the role "student", so an admin
account can only be made by someone with access to the server.
"""
import click
from flask.cli import with_appcontext
from werkzeug.exceptions import Conflict

from ..errors import ValidationError
from .service import AuthService
from .validators import validate_registration


@click.command("create-admin")
@click.option("--email", prompt=True)
@click.option("--full-name", prompt=True, default="Administrator")
@click.password_option()
@with_appcontext
def create_admin_command(email, full_name, password):
    try:
        data = validate_registration({"email": email, "password": password, "full_name": full_name})
        user = AuthService().register(data["email"], data["password"], data["full_name"], role="admin")
    except ValidationError as err:
        raise click.ClickException("; ".join(f"{field} {message}" for field, message in err.errors.items()))
    except Conflict as err:
        raise click.ClickException(err.description)
    click.echo(f"Admin {user.email} created (id {user.id}).")
