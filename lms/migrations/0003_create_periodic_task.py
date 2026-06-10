from django.db import migrations
from django_celery_beat.models import PeriodicTask, CrontabSchedule


def create_periodic_task(apps, schema_editor):
    # Создаем расписание: каждый день в 00:00
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='0',
        day_of_month='*',
        month_of_year='*',
        day_of_week='*',
        timezone='Europe/Moscow'
    )

    # Создаем периодическую задачу
    PeriodicTask.objects.get_or_create(
        name='Deactivate inactive users',
        defaults={
            'task': 'lms.tasks.deactivate_inactive_users',
            'crontab': schedule,
            'enabled': True,
        }
    )


def delete_periodic_task(apps, schema_editor):
    PeriodicTask.objects.filter(name='Deactivate inactive users').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('lms', '0002_auto_...'),  # Замените на последнюю миграцию
        ('django_celery_beat', '0015_...'),  # Зависимость от django_celery_beat
    ]

    operations = [
        migrations.RunPython(create_periodic_task, delete_periodic_task),
    ]