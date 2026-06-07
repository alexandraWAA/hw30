from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from lms.validators import validate_youtube_url


class Course(models.Model):
    """
    Модель курса
    """
    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Введите название курса'
    )
    preview = models.ImageField(
        upload_to='course_previews/',
        verbose_name='Превью',
        blank=True,
        null=True,
        help_text='Загрузите изображение для превью'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Введите описание курса',
        blank=True,
        null=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Владелец',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Lesson(models.Model):
    """
    Модель урока
    """
    name = models.CharField(
        max_length=200,
        verbose_name='Название',
        help_text='Введите название урока'
    )
    description = models.TextField(
        verbose_name='Описание',
        help_text='Введите описание урока',
        blank=True,
        null=True
    )
    preview = models.ImageField(
        upload_to='lesson_previews/',
        verbose_name='Превью',
        blank=True,
        null=True,
        help_text='Загрузите изображение для превью'
    )
    video_url = models.URLField(
        verbose_name='Ссылка на видео',
        help_text='Введите ссылку на видео (только YouTube)',
        blank=True,
        null=True,
        validators=[validate_youtube_url]  # Добавляем валидатор
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс',
        help_text='Выберите курс, к которому относится урок'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Владелец',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.course.name})"


class Subscription(models.Model):
    """
    Модель подписки на обновления курса
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Курс'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        unique_together = ['user', 'course']  # Гарантируем уникальность пары
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} -> {self.course.name}"