# University Room Management & Smart Scheduling System

**UE606 Software Engineering · Final Project · Proposal**
Analysed against PW#1–PW#8 · Team of 5

## Project summary

A university room-management platform with two roles: students and staff browse room availability and reserve rooms for events; administrators import academic schedules and exam dates from the university database, then run a scheduling engine that assigns suitable rooms without conflicts. The application is delivered as a containerised Python service through the full PW#1–PW#8 workflow.

---

## 1. Main Idea

**Problem.** University rooms are needed for lectures, tutorials, exams, meetings and student events. When room availability is tracked manually or across separate systems, double bookings can occur, rooms may be assigned to unsuitable activities, and event organisers cannot easily see which rooms are genuinely free. Administrators also need to coordinate room assignments around existing professor timetables and examination periods.

**Solution.** Build one central platform with a public user interface and a protected administrator panel. The public side displays room availability and lets authenticated users request or book a free room for an event. The admin side connects to the university scheduling database (or, for the academic prototype, an imported/simulated data source), retrieves professor schedules and exam slots, and runs a Schedule Engine to allocate rooms automatically. The engine checks room capacity, room type, time overlaps and existing reservations before publishing the resulting room plan.

### Two operating modes

| Regular user                                                                                                                                                                                                 | Administrator                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Browse the timetable and room calendar; filter by date, time, building, capacity and room type; view free/busy slots; submit a room booking for an event; see booking status and cancel an eligible request. | Sign in to a protected admin panel; synchronise/import professor timetables and exam periods; maintain room metadata; run the Schedule Engine; review conflicts and proposed allocations; approve, publish or manually adjust the schedule. |

### Core scheduling rules

1. A room cannot host two activities at the same time.
2. Room capacity must be at least the expected group size.
3. Activity requirements must match the room type/equipment.
4. Existing lectures, professor schedules and exams are treated as blocked time.
5. Event bookings cannot overlap with academic allocations or other confirmed bookings.
6. Only administrators can publish or override the official academic room plan.

**Scope.** The project is an educational prototype, not a replacement for the university's official timetable system. If direct database access is not granted, use a documented CSV/JSON import adapter with realistic sample data. Authentication, role-based access, booking validation, schedule generation and deployment remain in scope.

---

## 2. Relation to PWs

The project follows the Python web-application track. Each practical work becomes a concrete stage in building, testing, packaging, deploying and monitoring the same application. The table maps the typical PW#1–PW#8 topics shown in the supplied reference to this project; adjust names or required platforms if your instructor's official PW sheet differs.

| PW  | Lab focus              | Project deliverable                                                                | Acceptance evidence / must-fix                                                                                                               |
| --- | ---------------------- | ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| #1  | Git and collaboration  | Repository, `src/` structure, README, feature branches and pull requests.          | All five members contribute through branches; reviewed PRs merge into `main`; no shared unreviewed commits.                                  |
| #2  | Python web framework   | FastAPI application with health, room, availability, booking and admin routes.     | `GET /health`; `GET /api/v1/rooms`; `GET /api/v1/availability`; `POST /api/v1/bookings`; admin-only schedule endpoints.                      |
| #3  | pytest                 | Unit and API tests for booking validation, permissions and scheduling constraints. | Test success and failure cases: overlapping booking, insufficient capacity, wrong room type, unauthorised admin request, invalid time range. |
| #4  | Continuous Integration | GitHub Actions workflow runs linting and tests on push and pull request.           | A failing test blocks a green pipeline; tests run automatically for every PR to `main`.                                                      |
| #5  | Docker                 | Dockerfile and `docker-compose.yml` for API, database and supporting services.     | A teammate can clone the repository and start the application with one documented command, e.g. `docker compose up --build`.                 |
| #6  | Continuous Deployment  | Build and publish a versioned container image after a successful merge to `main`.  | Image is tagged with `latest` and the commit SHA; deployment only runs after tests pass.                                                     |
| #7  | Cloud deployment       | Deploy the API and database-backed service to an approved hosting platform.        | Public demo URL, environment-based configuration, persistent database storage and a working `/health` endpoint.                              |
| #8  | Monitoring             | Application logs, uptime checks and basic operational dashboard/alerts.            | Demonstrate a failed health check or service interruption and document recovery/rollback.                                                    |

**Why the fit is strong.** The application naturally demonstrates the full software lifecycle: source control and team collaboration, a Python REST API, automated tests, CI, Docker packaging, deployment and monitoring. It also has testable business rules rather than being only a basic database interface. The Schedule Engine provides a clear algorithmic component that can be benchmarked and defended.

**Suggested API surface.**

- Public: `GET /health`, `GET /api/v1/rooms`, `GET /api/v1/availability`, `POST /api/v1/bookings`, `GET /api/v1/bookings/me`.
- Admin: `POST /api/v1/admin/sync`, `POST /api/v1/admin/schedule/generate`, `GET /api/v1/admin/schedule/conflicts`, `POST /api/v1/admin/schedule/publish`.

Protect admin routes with role-based access control.

---

## 3. Technical Aspect

**Architecture.** Use a modular monolith for the first version: one FastAPI backend divided into independent modules, plus separate Docker services for PostgreSQL and Redis (optional). This is easier for a five-person student team to integrate than premature microservices, while still demonstrating container networking and server-side components.

| Component                    | Responsibility                                                                                         | Suggested technology                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| Client / Admin UI            | Room calendar, filters, booking flow and protected admin dashboard.                                    | Simple server-rendered templates or a small frontend; keep UI scope controlled.       |
| API server                   | Authentication, role checks, validation, room/booking endpoints and orchestration.                     | Python 3.12, FastAPI, Pydantic, Uvicorn                                               |
| Schedule Engine              | Reads academic activities and room constraints; allocates rooms; returns assignments and conflicts.    | Python classes; greedy baseline, then backtracking/constraint search if time permits. |
| Database                     | Stores rooms, users, roles, event requests, reservations, imported activities and generated schedules. | PostgreSQL, SQLAlchemy, Alembic                                                       |
| Background worker (optional) | Runs longer schedule-generation or import jobs without blocking API requests.                          | Redis + Celery/RQ; add only if needed.                                                |
| Reverse proxy / delivery     | Routes external HTTP traffic and supports container deployment.                                        | Nginx (optional), Docker, Docker Compose, GitHub Actions                              |

**Data flow.**

1. Admin imports or synchronises professor timetables, exam slots, room data and capacity.
2. The backend normalises this data and stores it in PostgreSQL.
3. Admin starts schedule generation.
4. The engine builds a set of activities and candidate rooms, applies hard constraints and produces assignments plus unassigned items/conflict reasons.
5. Admin reviews and publishes the result.
6. Public availability is calculated from published academic allocations plus confirmed event bookings.
7. A user submits a booking; the API rechecks availability inside a database transaction before confirming it, preventing race-condition double bookings.

**Schedule Engine approach.** Model each lecture/exam/event as an activity with start time, end time, expected group size and required room features. Candidate rooms are filtered by capacity and type. A first-fit/greedy allocator is a realistic minimum deliverable. If time permits, improve it with backtracking and a heuristic such as "most constrained activity first". Report assigned activities, unassigned activities, conflict reasons and runtime. Do not promise a globally optimal schedule unless the algorithm actually proves optimality.

**Important integration boundary.** Direct access to the university's live database depends on permission, credentials, schema documentation and network access. The project should therefore define a `UniversityDataProvider` interface. Implement a CSV/JSON provider for development and testing; a real database adapter can replace it if the university grants access. Never hard-code credentials or expose the university database directly to public users.

---

## 4. Execution Time (team of 5)

**Planning assumption:** 4 weeks, approximately 9 hours per person per week (about 180 person-hours total). This is a realistic prototype estimate if the team keeps the frontend simple and uses a CSV/JSON adapter unless live database access is already available. A production-ready university integration would require additional time and approval.

| Member                                | Feature they code                                                                                                                                                                                                                                                     | Design pattern                                                                                                                                                                     | PW they set up                                                                                                                             |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **A – Ilaha**<br>Rooms & core app     | App structure (`create_app()`, Blueprints, Dev/Test/Prod config), Swagger UI, room management (admin adds/edits rooms, types, equipment), `GET /rooms` with filters, `GET /availability`.                                                                             | **Factory** (`create_app(config)` builds the app from a config) + **Facade** (one `AvailabilityService` hides how lectures, exams and bookings are combined into free/busy times). | **PW1** repo, branch protection, Issues board + **PW2** setup (Flask, venv, `requirements.txt`).                                           |
| **B – Javid**<br>Auth & bookings      | Register/login, user roles, `POST /bookings`, `GET /bookings/me`, cancel booking, recheck inside a database transaction so two people can't book the same room at once.                                                                                               | **Decorator** (`@login_required`, `@role_required("admin")`) + **Chain of Responsibility** (a booking goes through checks in order: time range → capacity → room type → overlap).  | **PW3 setup** (`conftest.py`, shared test fixtures, test database) + **PW4 CI** (lint + tests on every PR, coverage report).               |
| **C – Bahruz**<br>Database & import   | SQLAlchemy models, migrations, sample-data script, CSV/JSON importer, `POST /admin/sync`.                                                                                                                                                                             | **Repository** (`RoomRepository`, `BookingRepository`, so no raw queries elsewhere in the code) + **Adapter** (CSV and JSON both converted into the same `Activity` format).       | **PW5** `Dockerfile` + `docker-compose.yml` (app + Postgres), a volume so data survives restarts, `.env.example`.                          |
| **D – Said**<br>Schedule engine       | Constraint checks (capacity, room type, time overlap, times already blocked), greedy allocator, conflict report, benchmark script, `/admin/schedule/generate`, `/conflicts`, `/publish`.                                                                              | **Strategy** (`GreedyAllocator` and `BacktrackingAllocator` can be swapped without changing other code; each rule is its own small class).                                         | **PW6 CD** (build the image, push to GHCR tagged `latest` and with the commit SHA, only after tests pass).                                 |
| **E – Teymur**<br>Events & operations | Event system: events `BookingCreated`, `BookingCancelled` and `SchedulePublished`, with listeners that save in-app notifications and write an audit log. Endpoints: `GET /notifications/me`, `GET /admin/audit-log`, `GET /admin/stats` (how much each room is used). | **Observer** (B's and D's code only sends events and doesn't know who is listening).                                                                                               | **PW7** Render deployment (`render.yaml`, Render Postgres, environment variables) + **PW8** (request logging, UptimeRobot, rollback demo). |

**Milestones and validation targets** (estimates, to be measured):

- **End of Week 1:** repository, data model and API skeleton run locally.
- **End of Week 2:** users can view rooms and availability; basic booking and greedy room allocation work.
- **End of Week 3:** admin import/generation flow, conflict checks, role permissions and CI tests are integrated.
- **End of Week 4:** Docker deployment, monitoring, end-to-end demonstration and documentation are complete.

**Performance targets.**

- Room availability query: under 300 ms on seeded demo data (excluding cold start).
- Booking validation and persistence: under 500 ms under light load.
- Greedy generation for a sample dataset of 100–300 activities and 20–50 rooms: target under 2 seconds on a student laptop.

These are engineering targets, not measured results; include a benchmark script and report actual numbers in the final submission.

**Risks / scope control.** The largest risk is unavailable or undocumented university database access. Mitigate with a provider interface and realistic synthetic data. Do not attempt live integration, complex optimisation, payment, mobile apps or enterprise-grade identity management unless the core workflow is already complete.
