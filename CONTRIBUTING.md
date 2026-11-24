# How we work together

This is our team agreement for Git and GitHub (PW#1). Everyone follows it, so
the teacher can see in the history that all five of us contributed.

## The golden rule

**Nobody pushes to `main`.** All work goes through a branch and a pull request
that a teammate reviews. GitHub enforces this (see "Branch protection" below).

## Daily workflow

```bash
git checkout main
git pull                                   # get everyone's latest work
git checkout -b feature/rooms-filters      # one branch per task
# ...write code and tests...
pytest                                     # all tests must pass locally
git add .
git commit -m "Add equipment filter to GET /rooms"
git push -u origin feature/rooms-filters
```

Then open a pull request on GitHub into `main`, link the issue
(write `Closes #12` in the description) and ask one teammate to review.

## Branch names

| Prefix      | Use it for                    | Example                         |
|-------------|-------------------------------|---------------------------------|
| `feature/`  | New functionality             | `feature/booking-chain`         |
| `fix/`      | Bug fixes                     | `fix/availability-timezone`     |
| `docs/`     | README, docs, comments only   | `docs/readme-architecture`      |
| `ci/`       | Workflows, Docker, deployment | `ci/docker-compose`             |
| `test/`     | Tests only                    | `test/schedule-engine-edges`    |

## Commit messages

Short, in English, imperative mood, saying *what* changed:

- Good: `Add Facade for room availability`
- Bad: `update`, `fix stuff`, `final version 2`

## Pull requests

- Small PRs are reviewed faster. One task per PR.
- CI (PW#4) must be green before merging.
- At least **one approval** from another member.
- The author merges after approval, then deletes the branch.

## Branch protection (set up once by Part A)

GitHub → repository → **Settings → Branches → Add branch ruleset** (or "Add rule"):

1. Branch name pattern: `main`
2. Tick **Require a pull request before merging** → required approvals: **1**
3. Tick **Require status checks to pass** → select the CI job `build-and-test`
   (it appears in the list after the CI workflow from PW#4 has run once)
4. Tick **Block force pushes**
5. Save

## Issues board (set up once by Part A)

GitHub → **Projects → New project → Board**, link it to the repository, columns:
`Backlog` → `To do` → `In progress` → `In review` → `Done`.

- Every task is an issue, assigned to one person, with a label for the part:
  `part-A` `part-B` `part-C` `part-D` `part-E`, plus `bug` / `docs` / `devops`.
- Move your card when you start, open a PR, and finish.

## Project layout

```
src/app/               the Flask application (create_app lives in __init__.py)
  config.py            Dev / Test / Prod settings
  models/              SQLAlchemy tables                      (Part C)
  repositories/        all database queries                    (Part C)
  rooms/               room management endpoints               (Part A)
  availability/        free/busy times, Facade                 (Part A)
  auth/                login, roles, decorators                (Part B)
tests/                 pytest tests, one file per feature
.github/workflows/     CI and CD                               (Parts B, D)
```

Put new features in their own package under `src/app/` with a blueprint, and
register it in `create_app()`.
