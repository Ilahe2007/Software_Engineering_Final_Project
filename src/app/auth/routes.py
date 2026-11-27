"""Register, log in, log out, and change a user's role (admin)."""
from flask import current_app, jsonify, request

from . import bp
from .decorators import current_user, login_required, role_required
from .service import AuthService
from .tokens import create_access_token
from .validators import validate_login, validate_registration, validate_role_change

auth = AuthService()


@bp.post("/register")
def register():
    """Create a student account.
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password, full_name]
          example: {email: "ali@ufaz.az", password: "a-long-passphrase", full_name: "Ali Aliyev"}
    responses:
      201: {description: Account created. The role is always "student".}
      400: {description: Invalid data, weak password, or a field that is not allowed (e.g. role).}
      409: {description: An account with this email already exists.}
    """
    data = validate_registration(request.get_json(silent=True))
    user = auth.register(data["email"], data["password"], data["full_name"])
    return jsonify(user.to_dict()), 201


@bp.post("/login")
def login():
    """Log in and get an access token.
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          example: {email: "ali@ufaz.az", password: "a-long-passphrase"}
    responses:
      200: {description: "The token. Send it as 'Authorization: Bearer <access_token>'."}
      401: {description: Wrong email or password (the same answer for both).}
      429: {description: Too many failed logins; the account is locked for a while.}
    """
    email, password = validate_login(request.get_json(silent=True))
    config = current_app.config
    user = auth.authenticate(email, password, config["MAX_FAILED_LOGINS"], config["LOCKOUT_MINUTES"])
    token = create_access_token(user, config["SECRET_KEY"], config["JWT_ACCESS_MINUTES"])
    return jsonify(
        access_token=token,
        token_type="Bearer",
        expires_in=config["JWT_ACCESS_MINUTES"] * 60,
        user=user.to_dict(),
    )


@bp.get("/me")
@login_required
def me():
    """The logged-in user.
    ---
    tags: [Auth]
    security: [{Bearer: []}]
    responses:
      200: {description: The user.}
      401: {description: Not logged in, or the token is invalid or expired.}
    """
    return jsonify(current_user().to_dict())


@bp.post("/logout")
@login_required
def logout():
    """Log out everywhere: every token issued so far stops working.
    ---
    tags: [Auth]
    security: [{Bearer: []}]
    responses:
      204: {description: Logged out.}
      401: {description: Not logged in.}
    """
    auth.logout(current_user())
    return "", 204


@bp.patch("/users/<int:user_id>/role")
@role_required("admin")
def change_role(user_id):
    """Change a user's role (admin). The user has to log in again.
    ---
    tags: [Auth (admin)]
    security: [{Bearer: []}]
    parameters:
      - {name: user_id, in: path, type: integer, required: true}
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [role]
          example: {role: "teacher"}
    responses:
      200: {description: Role changed.}
      400: {description: Unknown role.}
      403: {description: Only admins can change roles.}
      404: {description: No user with this id.}
      409: {description: Admins cannot change their own role.}
    """
    role = validate_role_change(request.get_json(silent=True))
    user = auth.change_role(current_user(), user_id, role)
    return jsonify(user.to_dict())
