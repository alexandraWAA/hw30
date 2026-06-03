from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    """
    Кастомная команда для создания групп
    """
    help = 'Создает группы для проекта'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Создание групп...'))

        # Создание группы "Модераторы"
        moderator_group, created = Group.objects.get_or_create(name='Модераторы')

        if created:
            self.stdout.write(self.style.SUCCESS(f'✅ Группа "{moderator_group.name}" создана'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Группа "{moderator_group.name}" уже существует'))

        self.stdout.write(self.style.SUCCESS('\n✅ Команда выполнена успешно!'))