import django.db.models.deletion
from django.db import migrations, models


def link_existing_attendance_to_events(apps, schema_editor):
    AttendanceRecord = apps.get_model('core', 'AttendanceRecord')
    Event = apps.get_model('core', 'Event')

    for record in AttendanceRecord.objects.filter(event__isnull=True):
        event = Event.objects.filter(
            title=record.event_name,
            event_date=record.event_date,
        ).order_by('id').first()
        if event:
            record.event = event
            record.save(update_fields=['event'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_merge_0009_adminchangelog_0009_document_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancerecord',
            name='event',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendance_records',
                to='core.event',
            ),
        ),
        migrations.RunPython(link_existing_attendance_to_events, migrations.RunPython.noop),
    ]
