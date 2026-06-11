import logging
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from celery.utils.log import get_task_logger

from lms.models import Course, Subscription

logger = get_task_logger(__name__)


def _send_email(subject, message, recipient_list):
    """
    Вспомогательная функция для отправки email (DRY)
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info('Письмо отправлено на %s', recipient_list)
        return True
    except Exception as e:
        logger.error('Ошибка отправки письма на %s: %s', recipient_list, e)
        return False


@shared_task
def send_course_update_notification(course_id, updated_fields):
    """
    Задача для отправки уведомлений подписчикам курса об обновлении
    """
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        logger.error('Курс %d не найден', course_id)
        return

    # Получаем подписчиков с email
    subscribers = Subscription.objects.filter(
        course=course,
        user__email__isnull=False
    ).select_related('user')

    if not subscribers.exists():
        logger.info('Нет подписчиков с email для курса %r', course.name)
        return

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

    success_count = 0
    for subscription in subscribers:
        if _send_email(subject, message, [subscription.user.email]):
            success_count += 1

    logger.info('Уведомления отправлены %d из %d подписчикам курса "%s"',
                success_count, subscribers.count(), course.name)
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
        logger.error('Курс %d или урок %d не найден', course_id, lesson_id)
        return

    # Проверка: отправляем уведомление, только если курс не обновлялся более 4 часов
    time_since_update = timezone.now() - course.updated_at
    if time_since_update < timedelta(hours=4):
        logger.info(
            'Курс %r обновлялся менее 4 часов назад. Уведомление не отправлено.',
            course.name
        )
        return

    subscribers = Subscription.objects.filter(
        course=course,
        user__email__isnull=False
    ).select_related('user')

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
        if _send_email(subject, message, [subscription.user.email]):
            success_count += 1

    return {'success_count': success_count, 'total': subscribers.count()}