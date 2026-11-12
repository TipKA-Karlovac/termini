"""Na PostgreSQL-u bazi zabranjuje dva rezervirana termina koji se preklapaju.

Provjera u kodu (booking.services.book) nije dovoljna sama: dva zahtjeva koja
stignu u istom trenutku mogu obje vidjeti termin kao slobodan. Isključujuće
ograničenje tada odbije drugi upis.

SQLite takva ograničenja nema; ondje istodobne upise sprječava zaključavanje
cijele baze pri upisu (transaction_mode=IMMEDIATE u postavkama).
"""

from django.db import migrations

CONSTRAINT = "booking_appointment_no_overlap"


def add_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        f"""
        ALTER TABLE booking_appointment
        ADD CONSTRAINT {CONSTRAINT}
        EXCLUDE USING gist (tstzrange(starts_at, ends_at) WITH &&)
        WHERE (status = 'booked')
        """
    )


def drop_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"ALTER TABLE booking_appointment DROP CONSTRAINT {CONSTRAINT}")


class Migration(migrations.Migration):
    dependencies = [("booking", "0001_initial")]

    operations = [migrations.RunPython(add_constraint, drop_constraint)]
