# ClinicFlow

Appointment and queue management for private outpatient clinics in Addis Ababa.
This repository holds the MVP described in the ClinicFlow Ethiopia BRD (v1.0, 20 Nov 2026).

## Stack

| Part | Choice | Why |
| --- | --- | --- |
| API | Django 5.2 LTS + Django REST Framework | Built-in admin, auth, permissions and translations |
| Database | PostgreSQL 17 | Every clinic-owned row carries `clinic_id` |
| Live queue | Django Channels + Redis | WebSocket updates within seconds (NFR-11) |
| Background jobs | Celery + Redis | SMS reminders and exports off the request path |
| Web app | React + TypeScript (Vite), Carbon Design System, i18next | Same design system as OpenMRS 3; Amharic and English UI (NFR-13) |
| Hosting | Docker Compose on one Linux server | Portable to an Ethiopian data centre (NFR-01) |

## Layout

```
backend/
  config/            settings, URLs, ASGI (HTTP + WebSockets), Celery
  apps/core/         tenant-scoped base model and viewset, role permissions, audit log
  apps/tenants/      Clinic (the tenant)
  apps/accounts/     staff users, roles, login/logout/me API
  apps/scheduling/   practitioners, services, working hours, time off, appointments
  tests/             tenant isolation, role and audit tests
frontend/            React web app on Carbon (appointments, schedules, practitioners; Amharic/English)
```

## How clinic data is kept apart

- Every clinic-owned model extends `apps.core.models.TenantScopedModel`.
- Every API for those models extends `apps.core.viewsets.ClinicScopedViewSet`, which filters by the
  signed-in user's clinic and stamps new records with it. A record from another clinic returns 404.
- Platform support accounts have no clinic and cannot read clinic data through the API.
- `tests/test_tenant_isolation.py` must keep passing. Add a case there for every new module.

## Run it locally

With Docker:

```bash
docker compose up --build
docker compose exec api python manage.py createsuperuser
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Without Docker (Python 3.12+, Node 22, local Postgres or SQLite):

```bash
python -m venv .venv && . .venv/bin/activate
cd backend
pip install -r requirements-dev.txt
cp .env.example .env            # set DATABASE_URL=sqlite:///db.sqlite3 for a quick start
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver      # API on :8000, admin at /admin/
```

Then in another terminal: `cd frontend && npm install && npm run dev`.

Create a clinic and staff users in `/admin/`, then sign in to the web app as a staff user.

## How double-booking is prevented (FR-012)

Every booking and reschedule goes through `apps/scheduling/booking.py:place()`, which locks the
practitioner's row, checks working hours, time off and existing appointments, then saves. On
PostgreSQL an exclusion constraint (migration `scheduling/0003`) also makes overlapping active
appointments for one practitioner impossible at the database level. SQLite has no such
constraint, so use PostgreSQL for anything beyond a quick local look.

## Checks

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run build
```

## MVP build order

1. **Foundations** (this commit): tenants, staff roles, audit log, auth, Amharic/English shell.
2. **Schedules and bookings** (done): working hours, breaks, time off, booking without
   double-booking, reschedule/cancel, day and week views, status counts (FR-010 to FR-016).
3. **Check-in and queue**: walk-ins, queue states, live updates, anonymous waiting-room display
   (FR-020 to FR-037).
4. **Reports, exports, SMS and pilot readiness**: daily counts, wait times, CSV export, consent-gated
   SMS, backups and restore drill (FR-040 to FR-055, NFR-06, NFR-07).
