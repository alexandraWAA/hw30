import re
from django.core.exceptions import ValidationError


def validate_youtube_url(value):
    """
    Валидатор для проверки, что ссылка ведет на youtube.com
    """
    if not value:
        return

    # Регулярное выражение для проверки YouTube ссылок
    youtube_patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtu\.be/[\w-]+',
        r'^https?://(www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',
    ]

    is_valid = False
    for pattern in youtube_patterns:
        if re.match(pattern, value):
            is_valid = True
            break

    if not is_valid:
        raise ValidationError(
            'Разрешены только ссылки на YouTube (youtube.com, youtu.be). '
            'Пожалуйста, используйте корректную ссылку на видео.'
        )