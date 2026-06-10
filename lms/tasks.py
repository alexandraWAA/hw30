import logging
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from celery.utils.log import get_task_logger

from users.models import User
from lms.models import Course, Subscription

logger = get_task_logger(__name__)


@shared_task
def send_course_update_notification(course_id, updated_fields):
    """
    Задача для отправки уведомлений подписчикам курса об обновлении
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        logger.error(f'Курс {course_id} не найден')
        return

    # Получаем всех подписчиков курса
    subscribers = Subscription.objects.filter(course=course).select_related('user')

    if not subscribers.exists():
        logger.info(f'Нет подписчиков для курса {course.name}')
        return

    # Формируем сообщение
    subject = f'Обновление курса: {course.name}'
    message = f"""
    Здравствуйте!

    Курс "{course.name}" был обновлен.

    Обновленные поля: {', '.join(updated_fields)}

    Перейдите на платформу, чтобы ознакомиться с обновлениями:
    http://localhost:8000/api/lms/courses/{course_id}/

    С уважением,
    Команда LMS
    """

    # Отправляем письма всем подписчикам
    success_count = 0
    for subscription in subscribers:
        user = subscription.user
        if user.email:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                success_count += 1
                logger.info(f'Уведомление отправлено пользователю {user.email}')
            except Exception as e:
                logger.error(f'Ошибка отправки письма {user.email}: {e}')

    logger.info(f'Уведомления отправлены {success_count} подписчикам курса "{course.name}"')
    return {'success_count': success_count, 'total': subscribers.count()}


@shared_task
def send_lesson_update_notification(lesson_id, course_id, updated_fields):
    """
    * Дополнительное задание: отправка уведомления при обновлении урока
    с проверкой, что курс не обновлялся более 4 часов
    """
    try:
        course = Course.objects.get(pk=course_id)
        lesson = course.lessons.get(pk=lesson_id)
    except (Course.DoesNotExist, Lesson.DoesNotExist):
        logger.error(f'Курс {course_id} или урок {lesson_id} не найден')
        return

    # Проверка: отправляем уведомление, только если курс не обновлялся более 4 часов
    # (дополнительное задание)
    time_since_update = timezone.now() - course.updated_at
    if time_since_update < timedelta(hours=4):
        logger.info(f'Курс "{course.name}" обновлялся менее 4 часов назад. Уведомление не отправлено.')
        return

    subscribers = Subscription.objects.filter(course=course).select_related('user')

    if not subscribers.exists():
        return

    subject = f'Новый урок в курсе: {course.name}'
    message = f"""
    Здравствуйте!

    В курсе "{course.name}" появился новый урок или обновление.

    Урок: {lesson.name}
    Обновленные поля: {', '.join(updated_fields)}

    Перейдите на платформу, чтобы ознакомиться:
    http://localhost:8000/api/lms/courses/{course_id}/

    С уважением,
    Команда LMS
    """

    success_count = 0
    for subscription in subscribers:
        user = subscription.user
        if user.email:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                success_count += 1
            except Exception as e:
                logger.error(f'Ошибка отправки письма {user.email}: {e}')

    return {'success_count': success_count, 'total': subscribers.count()}


@shared_task
def deactivate_inactive_users():
    """
    Периодическая задача: блокировка пользователей,
    которые не заходили более месяца (30 дней)
    """
    one_month_ago = timezone.now() - timedelta(days=30)

    # Находим пользователей, которые не заходили более месяца
    inactive_users = User.objects.filter(
        last_login__lt=one_month_ago,
        is_active=True,
        is_superuser=False  # Не блокируем суперпользователей
    )

    count = inactive_users.count()

    if count > 0:
        # Обновляем батчем (массовое обновление)
        updated_count = inactive_users.update(is_active=False)
        logger.info(f'Деактивировано {updated_count} неактивных пользователей')
        return {'deactivated': updated_count}
    else:
        logger.info('Нет пользователей для деактивации')
        return {'deactivated': 0}


@shared_task
def send_welcome_email_task(user_id, user_email, user_name):
    """
    Задача для отправки приветственного письма при регистрации
    """
    subject = 'Добро пожаловать в LMS!'
    message = f"""
    Здравствуйте, {user_name}!

    Добро пожаловать на платформу онлайн-обучения LMS.

    Мы рады видеть вас среди наших студентов!

    С уважением,
    Команда LMS
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(f'Приветственное письмо отправлено пользователю {user_email}')
    except Exception as e:
        logger.error(f'Ошибка отправки приветственного письма: {e}')