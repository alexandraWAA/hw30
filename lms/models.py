from django.db import models


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
        help_text='Введите ссылку на видео',
        blank=True,
        null=True
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс',
        help_text='Выберите курс, к которому относится урок'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.course.name})"