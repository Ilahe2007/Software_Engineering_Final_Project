"""Registration, login, tokens and roles, including the attacks they must resist."""
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt

from app.auth.tokens import create_access_token
from app.extensions import db
from app.models import User
from conftest import TEST_PASSWORD

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"

NEW_USER = {"email": "Ali@UFAZ.az", "password": "a-long-passphrase", "full_name": "Ali Aliyev"}


def _login(client, email, password=TEST_PASSWORD):
    return client.post(LOGIN, json={"email": email, "password": password})


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _b64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


# --- Registration -----------------------------------------------------------------------------


def test_register_creates_a_student(client):
    response = client.post(REGISTER, json=NEW_USER)
    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "ali@ufaz.az"
    assert body["role"] == "student"
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_only_as_a_salted_hash(client):
    client.post(REGISTER, json=NEW_USER)
    user = db.session.scalar(db.select(User).where(User.email == "ali@ufaz.az"))
    assert user.password_hash.startswith("scrypt:")
    assert NEW_USER["password"] not in user.password_hash


def test_register_cannot_choose_the_admin_role(client):
    response = client.post(REGISTER, json={**NEW_USER, "role": "admin"})
    assert response.status_code == 400
    assert "role" in response.get_json()["details"]["unknown_fields"]
    assert db.session.scalar(db.select(User).where(User.email == "ali@ufaz.az")) is None


def test_register_same_email_twice_ignores_case(client):
    assert client.post(REGISTER, json=NEW_USER).status_code == 201
    again = {**NEW_USER, "email": "ali@ufaz.AZ"}
    assert client.post(REGISTER, json=again).status_code == 409


def test_register_reports_every_problem_at_once(client):
    response = client.post(REGISTER, json={"email": "not-an-email", "password": "short", "full_name": " "})
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"email", "password", "full_name"}


def test_register_refuses_common_passwords(client):
    response = client.post(REGISTER, json={**NEW_USER, "password": "Password123"})
    assert response.status_code == 400
    assert "common" in response.get_json()["details"]["password"]


def test_register_refuses_a_huge_password(client):
    response = client.post(REGISTER, json={**NEW_USER, "password": "x" * 10_000})
    assert response.status_code == 400


def test_register_needs_a_json_object(client):
    assert client.post(REGISTER, data="email=a@b.c").status_code == 400
    assert client.post(REGISTER, json=["a", "b"]).status_code == 400


# --- Login ------------------------------------------------------------------------------------


def test_login_returns_a_working_token(client, make_user):
    user = make_user("teacher", email="prof@ufaz.az")
    response = _login(client, "PROF@ufaz.az")
    assert response.status_code == 200
    body = response.get_json()
    assert body["token_type"] == "Bearer"
    assert body["user"]["role"] == "teacher"

    me = client.get(ME, headers=_bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.get_json()["id"] == user.id


def test_register_then_login(client):
    client.post(REGISTER, json=NEW_USER)
    assert _login(client, "ali@ufaz.az", NEW_USER["password"]).status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_answer(client, make_user):
    make_user(email="real@ufaz.az")
    wrong_password = _login(client, "real@ufaz.az", "wrong-password-123")
    unknown_email = _login(client, "nobody@ufaz.az", "wrong-password-123")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()


def test_login_needs_email_and_password(client):
    response = client.post(LOGIN, json={})
    assert response.status_code == 400
    assert set(response.get_json()["details"]) == {"email", "password"}


def test_deactivated_user_cannot_log_in(client, make_user):
    user = make_user(email="gone@ufaz.az")
    user.is_active = False
    db.session.commit()
    assert _login(client, "gone@ufaz.az").status_code == 401


# --- Brute-force protection -------------------------------------------------------------------


def test_account_is_locked_after_too_many_wrong_passwords(app, client, make_user):
    make_user(email="target@ufaz.az")
    for _ in range(app.config["MAX_FAILED_LOGINS"]):
        assert _login(client, "target@ufaz.az", "guess-guess-guess").status_code == 401

    # Even the right password is refused while the account is locked.
    assert _login(client, "target@ufaz.az").status_code == 429


def test_lock_expires(app, client, make_user):
    user = make_user(email="target@ufaz.az")
    for _ in range(app.config["MAX_FAILED_LOGINS"]):
        _login(client, "target@ufaz.az", "guess-guess-guess")
    user.locked_until = datetime.now() - timedelta(minutes=1)
    db.session.commit()
    assert _login(client, "target@ufaz.az").status_code == 200


def test_successful_login_resets_the_failure_count(app, client, make_user):
    user = make_user(email="target@ufaz.az")
    for _ in range(app.config["MAX_FAILED_LOGINS"] - 1):
        _login(client, "target@ufaz.az", "guess-guess-guess")
    assert _login(client, "target@ufaz.az").status_code == 200
    db.session.refresh(user)
    assert user.failed_login_count == 0


# --- Tokens -----------------------------------------------------------------------------------


def test_protected_endpoint_needs_a_token(client):
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Basic YWxpOnB3"}).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer"}).status_code == 401
    assert client.get(ME, headers=_bearer("not.a.jwt")).status_code == 401


def test_expired_token_is_refused(app, client, student_user):
    token = create_access_token(student_user, app.config["SECRET_KEY"], minutes=-1)
    assert client.get(ME, headers=_bearer(token)).status_code == 401


def test_token_signed_with_another_key_is_refused(client, student_user):
    now = datetime.now(timezone.utc)
    claims = {"sub": str(student_user.id), "ver": 0, "iat": now, "exp": now + timedelta(hours=1)}
    forged = jwt.encode(claims, "an-attacker-key-that-is-long-enough!!", algorithm="HS256")
    assert client.get(ME, headers=_bearer(forged)).status_code == 401


def test_unsigned_alg_none_token_is_refused(client, admin_user):
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {"sub": str(admin_user.id), "ver": 0, "iat": now, "exp": now + 3600}
    unsigned = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(claims)}."
    assert client.get(ME, headers=_bearer(unsigned)).status_code == 401


def test_token_of_a_deleted_user_is_refused(client, student_user, student_headers):
    db.session.delete(student_user)
    db.session.commit()
    assert client.get(ME, headers=student_headers).status_code == 401


def test_logout_invalidates_existing_tokens(client, student_headers):
    assert client.post(LOGOUT, headers=student_headers).status_code == 204
    assert client.get(ME, headers=student_headers).status_code == 401


def test_deactivating_a_user_invalidates_their_tokens(client, student_user, student_headers):
    student_user.is_active = False
    db.session.commit()
    assert client.get(ME, headers=student_headers).status_code == 401


# --- Roles ------------------------------------------------------------------------------------


def _role_url(user_id):
    return f"/api/v1/auth/users/{user_id}/role"


def test_admin_can_promote_a_student_to_teacher(client, admin_headers, student_user, student_headers):
    response = client.patch(_role_url(student_user.id), json={"role": "teacher"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["role"] == "teacher"
    # The old token is refused, so the user logs in again and gets the new role.
    assert client.get(ME, headers=student_headers).status_code == 401
    assert _login(client, student_user.email).get_json()["user"]["role"] == "teacher"


def test_student_cannot_change_roles(client, student_user, student_headers):
    response = client.patch(_role_url(student_user.id), json={"role": "admin"}, headers=student_headers)
    assert response.status_code == 403


def test_teacher_cannot_change_roles(client, student_user, teacher_headers):
    response = client.patch(_role_url(student_user.id), json={"role": "teacher"}, headers=teacher_headers)
    assert response.status_code == 403


def test_admin_cannot_change_own_role(client, admin_user, admin_headers):
    response = client.patch(_role_url(admin_user.id), json={"role": "student"}, headers=admin_headers)
    assert response.status_code == 409


def test_role_change_validates_input(client, admin_headers, student_user):
    assert client.patch(_role_url(student_user.id), json={"role": "root"}, headers=admin_headers).status_code == 400
    assert client.patch(_role_url(9999), json={"role": "teacher"}, headers=admin_headers).status_code == 404


# --- Admin bootstrap and HTTP headers ---------------------------------------------------------


def test_create_admin_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin", "--email", "Root@ufaz.az", "--full-name", "Root", "--password", "a-long-passphrase"],
    )
    assert result.exit_code == 0, result.output
    user = db.session.scalar(db.select(User).where(User.email == "root@ufaz.az"))
    assert user.role == "admin"


def test_create_admin_command_refuses_a_weak_password(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--email", "root@ufaz.az", "--full-name", "Root", "--password", "123"])
    assert result.exit_code != 0
    assert "password" in result.output


def test_api_responses_carry_security_headers(client):
    response = client.get("/api/v1/rooms")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]


def test_swagger_ui_is_not_blocked_by_the_api_csp(client):
    response = client.get("/docs/")
    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
