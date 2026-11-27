# University Room Management & Smart Scheduling

UE606 Software Engineering final project.

A web app to find free university rooms, book them for events, and
automatically assign rooms to lectures and exams without conflicts.

Built with Python and Flask. More documentation coming soon.

## Logging in

Register with `POST /api/v1/auth/register`, log in with `POST /api/v1/auth/login`,
then send the token as `Authorization: Bearer <access_token>`. In Swagger UI
(`/docs/`) click **Authorize** and paste `Bearer <access_token>`.

New accounts are always students. Create the first admin on the server:

```bash
cd src
APP_ENV=development flask --app run create-admin      # Linux / macOS
$env:APP_ENV="development"; flask --app run create-admin   # Windows PowerShell
```

An admin can then change roles with `PATCH /api/v1/auth/users/<id>/role`
(`student`, `teacher`, `admin`). See [docs/security.md](docs/security.md)
for how login, roles and bookings are protected.

## Checks before a pull request

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check src tests
bandit -r src -q -ll
pytest --cov=app
```

CI runs the same checks, plus `pip-audit` and a secret scan, on every pull request.
