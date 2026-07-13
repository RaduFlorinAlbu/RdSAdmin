from django.db import migrations


def backfill_centru(apps, schema_editor):
    """Backfill centru on existing Therapy records from therapist.centru."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            UPDATE core_therapy
            SET centru_id = core_therapist.centru_id
            FROM core_therapist
            WHERE core_therapy.therapist_id = core_therapist.id
              AND core_therapy.centru_id IS NULL
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_therapy_centru_snapshot'),
    ]

    operations = [
        migrations.RunPython(backfill_centru, migrations.RunPython.noop),
    ]
