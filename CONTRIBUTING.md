# Contributing to University Room Management

Thank you for working on this project! Five of us write code in the same
repository, so please follow the guidelines below. They keep the history
clean, the code consistent, and `main` always working.

## Table of Contents

- [Team Workflow](#-team-workflow)
  - [Daily Workflow](#daily-workflow)
  - [Branch Names](#branch-names)
  - [Commit Messages](#commit-messages)
  - [Pull Requests](#pull-requests)
  - [Issues Board](#issues-board)
- [Works on Every Machine](#-works-on-every-machine)
- [Python & Project Guidelines](#%EF%B8%8F-python--project-guidelines)
  - [Python Version](#python-version)
  - [Dependencies](#dependencies)
  - [Where Code Goes](#where-code-goes)
  - [Error Handling & Logging](#error-handling--logging)
  - [API Conventions](#api-conventions)
- [Naming Conventions](#%EF%B8%8F-naming-conventions)
- [Formatting Rules](#-formatting-rules)
- [Python Best Practices](#-python-best-practices)
- [Tests](#-tests)
- [One-Time Repository Setup](#-one-time-repository-setup)

## 🤝 Team Workflow

> [!IMPORTANT]
> Nobody pushes to `main`. All work goes through a branch and a pull request
> that a teammate reviews.

### Daily Workflow

```bash
git checkout main
git pull                                   # get everyone's latest work
git checkout -b feature/rooms-filters      # one branch per task
# ...write code and tests...
pytest                                     # all tests must pass locally
git add src/app/rooms/routes.py tests/test_rooms.py
git commit -m "Add equipment filter to GET /rooms"
git push -u origin feature/rooms-filters
```

Then open a pull request into `main` on GitHub and ask one teammate to review.

- Add files by name. Do not use `git add .`: it also commits files you did not mean to share.
- Commit small and often. One commit should do one thing.

### Branch Names

Use a prefix, then a short name in lowercase with hyphens:

| Prefix     | Use it for                    | Example                      |
|------------|-------------------------------|------------------------------|
| `feature/` | New functionality             | `feature/booking-chain`      |
| `fix/`     | Bug fixes                     | `fix/availability-timezone`  |
| `docs/`    | README, docs, comments only   | `docs/readme-architecture`   |
| `ci/`      | Workflows, Docker, deployment | `ci/docker-compose`          |
| `test/`    | Tests only                    | `test/schedule-engine-edges` |

### Commit Messages

Write them in English, in the imperative mood, saying what changed:

```
# Bad
update
fix stuff
final version 2

# Good
Add Facade for room availability
Reject bookings outside opening hours
```

### Pull Requests

- One task per pull request. Small pull requests are reviewed faster.
- Fill in the description: what it does, which part it belongs to, the checklist.
- CI must be green before merging.
- At least one approval from another member.
- The author merges after approval, then deletes the branch.

### Issues Board

- Every task is an issue, assigned to one person, with a label for the part:
  `part-A` `part-B` `part-C` `part-D` `part-E`, plus `bug` / `documentation` / `devops`.
- Move your card when you start, when you open a pull request, and when it is merged.
- Write `Closes #12` in the pull request description to close the issue automatically.

## 🌍 Works on Every Machine

We use Windows and Linux. Code that runs on your laptop must also run on a
teammate's laptop, in CI, in Docker and on Render.

- Work inside a virtual environment (`.venv`) and install with `pip install -r requirements.txt`.
- Start the app with `python src/run.py --dev`. This works the same on every operating system.
- Never write absolute paths such as `C:\Users\...` or `/home/...` in the code.
- Read settings from environment variables through `config.py`, never from hard-coded values.
- File and folder names are lowercase. Linux treats `Rooms.py` and `rooms.py` as different files.

> [!IMPORTANT]
> Never commit `.venv/`, `.env`, `*.db` or `__pycache__/`. They are in
> `.gitignore`; do not remove them from it. Passwords and secret keys never
> go into the repository.

## ⚙️ Python & Project Guidelines

### Python Version

The project targets Python 3.12, the version in our Docker image. Do not use
features that are newer than the Python version in our CI workflow.

### Dependencies

- Do not add a package without a reason. Check first whether Flask, SQLAlchemy
  or the standard library already does the job.
- Add new packages to `requirements.txt` with a pinned version (`Flask==3.1.3`).
- Mention every new package in the pull request description.

### Where Code Goes

```
src/app/
  __init__.py      create_app()                          Factory
  config.py        Development / Testing / Production
  models/          SQLAlchemy tables
  repositories/    all database queries                  Repository
  <feature>/       one folder per feature, with a blueprint
    routes.py      endpoints: read input, call logic, return JSON
    validators.py  checks for request data
    service.py     logic that is more than one query
tests/             one test file per feature
```

- Each feature lives in its own package with a blueprint, registered in `create_app()`.
- Database queries live only in `repositories/`. Routes and services never build queries.
- Routes stay short. Logic goes into a service or a validator.
- Do not change another member's package without telling them. Open an issue or ask in the pull request.

### Error Handling & Logging

- Do not silently ignore errors. Never write an empty `except:`.
- Catch the specific exception you expect. A broad `except Exception` is only for places where every failure is handled the same way, such as `/health`.
- For bad request data, raise `ValidationError` with a message per field. It becomes a 400 response.
- For other HTTP errors use `abort(404, "Room 7 not found.")` with a message that names the problem.
- Do not use `print()` in application code. Use `current_app.logger`.

```python
# Bad
try:
    capacity = int(raw)
except:
    pass

# Good
try:
    capacity = int(raw)
except ValueError:
    raise ValidationError({"min_capacity": "must be a whole number"})
```

### API Conventions

- All endpoints are under `/api/v1`.
- URLs use lowercase plural nouns with hyphens: `/rooms`, `/room-types`, `/bookings/me`.
- JSON keys use `snake_case`: `room_type`, `min_capacity`.
- Every response is JSON, including errors.
- Every endpoint has a Swagger docstring, so it appears at `/docs/`.
- Times are local university time in ISO format without a timezone: `2026-12-01T10:00`.
- A time range includes its start and excludes its end. `10:00–12:00` and `12:00–13:00` do not overlap.

| Status | Use it when                                         |
|--------|-----------------------------------------------------|
| 200    | The request worked                                  |
| 201    | Something was created                               |
| 204    | Something was deleted, nothing to return            |
| 400    | The request data is invalid                         |
| 401    | The user is not logged in                           |
| 403    | The user is logged in but not allowed               |
| 404    | The thing does not exist                            |
| 409    | Conflict: duplicate name, room already booked       |

> [!NOTE]
> Admin-only endpoints carry `@role_required("admin")` directly above the
> view function. Do not check roles by hand inside a view.

## 🏷️ Naming Conventions

### Quick Reference

| Element               | Style                  | Example                               |
|-----------------------|------------------------|---------------------------------------|
| Modules & packages    | `snake_case`           | `room_repository.py`, `availability/` |
| Classes               | `PascalCase`           | `RoomRepository`, `BusySlot`          |
| Exceptions            | `PascalCase`           | `ValidationError`                     |
| Functions & methods   | `snake_case`           | `list_rooms()`, `free_ranges()`       |
| Variables & arguments | `snake_case`           | `min_capacity`, `room_type`           |
| Constants             | `UPPER_SNAKE_CASE`     | `ROOM_FIELDS`, `OPENING_HOUR`         |
| Private helpers       | `_` + `snake_case`     | `_parse_date()`, `_busy_by_room()`    |
| Models                | singular `PascalCase`  | `Room`, `RoomType`                    |
| Table names           | plural `snake_case`    | `rooms`, `room_types`                 |
| Blueprints            | `bp` inside the package | `bp = Blueprint("rooms", __name__)`  |
| Test functions        | `test_` + what happens | `test_duplicate_room_code`            |

### Classes

Use `PascalCase`. The name describes a thing, not an action:

```python
class RoomRepository: ...
class AvailabilityService: ...
```

### Functions and Methods

Use `snake_case`. The name describes an action and starts with a verb:

```python
def list_rooms(): ...
def validate_room_payload(data): ...
def is_free(room_id, start, end): ...
```

### Variables

Use `snake_case` and full words. A reader should not have to guess:

```python
# Bad
rt = data["room_type"]
n = len(result)

# Good
room_type = data["room_type"]
room_count = len(result)
```

### Constants

Use `UPPER_SNAKE_CASE` at the top of the module:

```python
REQUIRED_ON_CREATE = {"code", "building", "capacity", "room_type"}
```

## 📐 Formatting Rules

We follow [PEP 8](https://peps.python.org/pep-0008/). The main points:

### Indentation

- Always use 4 spaces. Tabs are forbidden.
- Set your editor to insert spaces when you press Tab.

### Line Length

Keep lines under 120 characters. The only exception is a Swagger parameter
line inside a docstring.

### Strings

Use double quotes, and f-strings to build text:

```python
abort(404, f"Room {room_id} not found.")
```

### Blank Lines

- Two blank lines between top-level functions and classes.
- One blank line between methods inside a class.

### Imports

Group imports in three blocks, separated by a blank line, each block sorted
alphabetically:

1. Python standard library
2. Third-party packages (Flask, SQLAlchemy)
3. Our own project

```python
from datetime import date, datetime

from flask import abort, jsonify, request

from ..errors import ValidationError
from ..repositories import RoomRepository
from . import bp
```

- Inside `src/app`, use relative imports (`from ..extensions import db`).
- Do not use `from module import *`.
- Remove imports you no longer use.

### Wrapping

When a call with many arguments does not fit on one line, put each argument
on its own line and end with a trailing comma:

```python
room = Room(
    code=data["code"],
    building=data["building"],
    capacity=data["capacity"],
)
```

## 💡 Python Best Practices

### Use Early Returns

Check for problems first and leave. Do not nest the main logic inside `if` blocks:

```python
# Avoid
room = rooms.get(room_id)
if room is not None:
    if room.is_active:
        return jsonify(room.to_dict())

# Prefer
room = rooms.get(room_id)
if room is None or not room.is_active:
    abort(404, f"Room {room_id} not found.")
return jsonify(room.to_dict())
```

### Keep Routes Thin

A route reads the request, calls a validator, a repository or a service, and
returns JSON. It contains no query and no business rule:

```python
@bp.get("/rooms")
def list_rooms():
    filters = parse_room_filters(request.args)
    result = rooms.list_rooms(**filters)
    return jsonify(count=len(result), rooms=[room.to_dict() for room in result])
```

### Validate Everything That Comes From Outside

Never trust request data. Check the type and the range of every field, and
report all problems in one response, not only the first one.

### Do Not Repeat Yourself

If the same lines appear in two places, move them into a function. Example:
`parse_room_filters()` is shared by `/rooms` and `/availability`.

### Comments

Comments explain why, not what:

```python
# Avoid: repeats the code
room.is_active = False  # set is_active to False

# Good: explains the reason
# Rooms are deactivated, not deleted, so old bookings still point somewhere.
room.is_active = False
```

Start a module with a short docstring when its purpose is not clear from its name.

> [!TIP]
> If your class implements a design pattern, name the pattern in its
> docstring. It helps the reader and it helps us in the final presentation.

## 🧪 Tests

- Every pull request that adds or changes behaviour includes tests.
- Test files are named `tests/test_<feature>.py`; test functions start with `test_`.
- The test name says what is checked: `test_create_room_needs_admin`.
- Test the failures as well as the successes: wrong data, missing login, duplicates.
- Use the shared fixtures in `tests/conftest.py` (`app`, `client`, `admin_headers`, `seeded`).
  Every test gets a new, empty in-memory database.
- Tests never depend on each other or on the order they run in.

```bash
pytest                        # everything
pytest tests/test_rooms.py    # one file
pytest -k availability -v     # tests whose name matches
```

## 🔧 One-Time Repository Setup

Done once by the repository owner.

**Branch protection.** GitHub → **Settings → Branches → Add branch ruleset**:

1. Target: the default branch (`main`)
2. Tick **Require a pull request before merging**, required approvals: **1**
3. Tick **Require status checks to pass** and select the CI job, once the CI workflow has run for the first time
4. Tick **Block force pushes**
5. Save

**Issues board.** GitHub → **Projects → New project → Board**, with the columns
`Backlog` → `To do` → `In progress` → `In review` → `Done`.
