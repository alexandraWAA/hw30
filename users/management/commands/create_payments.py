from django.core.management.base import BaseCommand
from users.models import User, Payment
from lms.models import Course, Lesson


class Command(BaseCommand):
    """
    Кастомная команда для создания тестовых платежей
    """
    help = 'Создает тестовые платежи для пользователей'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Создание тестовых платежей...'))

        # Получаем или создаем тестовые данные
        user1, _ = User.objects.get_or_create(
            email='student1@example.com',
            defaults={'first_name': 'Иван', 'last_name': 'Петров'}
        )

        user2, _ = User.objects.get_or_create(
            email='student2@example.com',
            defaults={'first_name': 'Мария', 'last_name': 'Иванова'}
        )

        # Получаем курсы и уроки (если они есть)
        course_python = Course.objects.first()
        lesson_first = Lesson.objects.first()

        payments_data = [
            {
                'user': user1,
                'course': course_python,
                'amount': 4990.00,
                'payment_method': Payment.TRANSFER,
            },
            {
                'user': user1,
                'lesson': lesson_first,
                'amount': 990.00,
                'payment_method': Payment.CASH,
            },
            {
                'user': user2,
                'course': Course.objects.last() if Course.objects.count() > 1 else course_python,
                'amount': 2990.00,
                'payment_method': Payment.TRANSFER,
            },
        ]

        created_count = 0
        for payment_data in payments_data:
            payment, created = Payment.objects.get_or_create(**payment_data)
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Создан платеж: {payment}')

        self.stdout.write(self.style.SUCCESS(f'✅ Создано {created_count} платежей'))