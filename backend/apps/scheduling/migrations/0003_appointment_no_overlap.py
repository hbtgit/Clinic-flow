"""Database-level guard against double-booking (FR-012).

On PostgreSQL an exclusion constraint makes it impossible for two active appointments of the
same practitioner to overlap, even if two requests race past the application check. SQLite
(quick local runs only) has no equivalent, so there the row lock in booking.py is the guard.
"""

from django.db import migrations

CONSTRAINT = "appointment_no_overlap"


def add_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    schema_editor.execute(
        f"ALTER TABLE scheduling_appointment ADD CONSTRAINT {CONSTRAINT} "
        "EXCLUDE USING gist (practitioner_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&) "
        "WHERE (status IN ('booked', 'confirmed'))"
    )


def drop_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        f"ALTER TABLE scheduling_appointment DROP CONSTRAINT IF EXISTS {CONSTRAINT}"
    )


class Migration(migrations.Migration):
    dependencies = [("scheduling", "0002_schedules_and_appointments")]

    operations = [migrations.RunPython(add_constraint, drop_constraint)]
