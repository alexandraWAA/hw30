import os
from celery import Celery

# Устанавливаем модуль настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Загружаем настройки из Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим и регистрируем задачи в приложениях
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')