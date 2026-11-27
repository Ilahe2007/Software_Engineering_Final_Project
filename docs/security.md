# Security: authentication, authorization and bookings (Part B)

How login, roles and bookings are protected, which attacks were considered,
and which test proves each protection. Code: `src/app/auth/`, `src/app/bookings/`.

## How login works

1. `POST /api/v1/auth/register` creates an account. The role is always `student`.
2. `POST /api/v1/auth/login` checks the password and returns a token (JWT, HS256,
   signed with `SECRET_KEY`, valid for `JWT_ACCESS_MINUTES`, 60 by default).
3. The client sends `Authorization: Bearer <token>` on every protected request.
4. `@login_required` / `@role_required("admin")` verify the signature and expiry, load
   the user **from the database**, and refuse the token if the user is gone, deactivated,
   or if the token is older than the user's last logout or role change (`token_version`).

The first admin is created on the server with `flask create-admin` (see README).
Admins promote other users with `PATCH /api/v1/auth/users/<id>/role`.

## Threat model (STRIDE)

| Threat | Example attack | Protection | Test |
|---|---|---|---|
| **S**poofing | Guess a password by trying many | Account locked for 15 min after 5 wrong passwords in a row (429) | `test_account_is_locked_after_too_many_wrong_passwords` |
| Spoofing | Find out which emails have an account | Same 401 message for unknown email and wrong password; a dummy hash check keeps the response time the same | `test_wrong_password_and_unknown_email_get_the_same_answer` |
| Spoofing | Forge a token | HS256 signature, key ≥ 32 bytes enforced in production | `test_token_signed_with_another_key_is_refused`, `test_production_refuses_a_short_secret_key` |
| Spoofing | Token with `"alg": "none"` (no signature) | Algorithm list fixed to `HS256` when decoding | `test_unsigned_alg_none_token_is_refused` |
| Spoofing | Reuse a stolen token after logout | Logout raises `token_version`; older tokens are refused | `test_logout_invalidates_existing_tokens` |
| **T**ampering | Book in another user's name, or set `status` | Unknown fields are rejected (no mass assignment); `user_id` comes from the token | `test_cannot_book_in_someone_elses_name` |
| Tampering | SQL injection | Every query goes through SQLAlchemy with bound parameters, only in `repositories/` | (by design; bandit runs in CI) |
| **R**epudiation | "I never cancelled that booking" | Bookings are cancelled, not deleted (`cancelled_at`); logins, lockouts, role changes and 403s are logged | — |
| **I**nformation disclosure | Read the password database | Only salted scrypt hashes are stored | `test_password_is_stored_only_as_a_salted_hash` |
| Information disclosure | Look at other users' bookings by changing the id (IDOR / BOLA) | Not the owner (and not admin) → 404, the same as "does not exist" | `test_cannot_cancel_someone_elses_booking` |
| Information disclosure | Tokens kept in browser or proxy caches | `Cache-Control: no-store` on every `/api/` response | `test_api_responses_carry_security_headers` |
| **D**enial of service | Send a 10 MB password to make hashing slow | Passwords limited to 128 characters | `test_register_refuses_a_huge_password` |
| Denial of service | Two people book the same room at the same moment | Room row locked (`SELECT ... FOR UPDATE`) and overlap rechecked inside one transaction | `test_room_is_locked_before_the_overlap_check` |
| **E**levation of privilege | Register with `"role": "admin"` | `role` is not an allowed field; registration is always `student` | `test_register_cannot_choose_the_admin_role` |
| Elevation of privilege | Student calls an admin endpoint | `@role_required("admin")`; the role is read from the database, not from the token | `test_create_room_needs_admin`, `test_student_cannot_change_roles` |
| Elevation of privilege | Keep admin rights after being demoted | Role change raises `token_version`; old tokens stop working | `test_admin_can_promote_a_student_to_teacher` |
| Elevation of privilege | The old `X-User-Role: admin` development header | Removed completely | `test_the_old_dev_role_header_no_longer_gives_admin_rights` |

## OWASP mapping

| OWASP | Where it is handled |
|---|---|
| A01 Broken Access Control / API1 BOLA / API5 BFLA | `auth/decorators.py`, ownership check in `bookings/service.py` |
| A02 Cryptographic Failures | scrypt password hashes, HS256 with a ≥ 32-byte key, HSTS in production |
| A03 Injection | SQLAlchemy only, inside `repositories/` |
| A04 Insecure Design | Chain of checks + row lock against double booking (`bookings/checks.py`) |
| A05 Security Misconfiguration | Production refuses to start without `DATABASE_URL` or with a weak `SECRET_KEY`; security headers (`auth/security_headers.py`) |
| A06 Vulnerable Components | `pip-audit` in CI |
| A07 Identification and Authentication Failures / API2 | Password rules, lockout, generic login errors, token expiry and revocation |
| A09 Logging and Monitoring Failures | Security events logged with `current_app.logger` (never passwords or tokens) |
| API3 Broken Object Property Level Authorization | Unknown request fields refused; `to_dict()` never returns `password_hash` |

## CI security checks (PW#4)

`.github/workflows/ci.yml` runs on every pull request:

- **ruff**: style and likely bugs.
- **bandit**: security lint of `src/` (fails on medium or high findings).
- **pip-audit**: known vulnerabilities in `requirements.txt`.
- **pytest + coverage**: fails under 85 %.
- **gitleaks**: committed passwords, keys and tokens, in the whole history.

## Known limits

- **Locked accounts answer 429**, so someone who triggers the lock learns that the email
  exists. Accepted: the alternative (a silent 401) would confuse real users.
- **The row lock only works on PostgreSQL.** SQLite (development and tests) ignores
  `FOR UPDATE`. A real two-thread race test needs the PostgreSQL from Part C's `docker-compose.yml`.
- **There is no refresh token.** After `JWT_ACCESS_MINUTES` the user logs in again.
- **No per-IP rate limit.** The lockout is per account; a rate limiter (e.g. Flask-Limiter)
  would also slow down guessing many accounts with one password.
