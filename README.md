# LMS Project

LMS (Learning Management System) - платформа для онлайн-обучения с REST API на Django REST Framework.

## 🚀 Технологии

- Python 3.10+
- Django 4.2.7
- Django REST Framework 3.14.0
- PostgreSQL
- Pillow

## 📦 Установка

```bash
# Клонирование
git clone <url>
cd lms_project

# Виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate

# Установка
pip install -r requirements.txt

# Настройка .env
cp .env.example .env

# Миграции
python manage.py migrate

# Запуск
python manage.py runserver