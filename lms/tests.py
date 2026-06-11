from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from lms.models import Course, Lesson, Subscription, Payment
from users.models import User

User = get_user_model()


class CourseTests(APITestCase):
    """Тесты для CRUD операций с курсами"""

    def setUp(self):
        """Подготовка тестовых данных"""
        # Создаем пользователей
        self.owner = User.objects.create_user(
            email='owner@test.com',
            password='testpass123',
            first_name='Owner'
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other'
        )
        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123',
            first_name='Moderator'
        )

        # Создаем группу модераторов
        from django.contrib.auth.models import Group
        moderator_group, _ = Group.objects.get_or_create(name='Модераторы')
        self.moderator.groups.add(moderator_group)

        # Создаем курс
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            price=1000,
            owner=self.owner
        )

        # Данные для создания курса
        self.course_data = {
            'name': 'New Course',
            'description': 'New Description',
            'price': 2000
        }

        # Аутентифицированные клиенты
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

        self.moderator_client = APIClient()
        self.moderator_client.force_authenticate(user=self.moderator)

        self.unauth_client = APIClient()

    # ========== ТЕСТЫ СОЗДАНИЯ ==========

    def test_create_course_success(self):
        """Тест успешного создания курса владельцем"""
        url = reverse('course-list')
        response = self.owner_client.post(url, self.course_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(Course.objects.last().name, 'New Course')
        self.assertEqual(Course.objects.last().owner, self.owner)

    def test_create_course_unauthorized(self):
        """Тест создания курса неавторизованным пользователем"""
        url = reverse('course-list')
        response = self.unauth_client.post(url, self.course_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_course_moderator_forbidden(self):
        """Тест: модератор не может создавать курсы"""
        url = reverse('course-list')
        response = self.moderator_client.post(url, self.course_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ========== ТЕСТЫ ПОЛУЧЕНИЯ ==========

    def test_get_course_list_owner(self):
        """Тест: владелец видит свои курсы"""
        url = reverse('course-list')
        response = self.owner_client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_course_list_moderator_sees_all(self):
        """Тест: модератор видит все курсы"""
        url = reverse('course-list')
        response = self.moderator_client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_course_detail_owner(self):
        """Тест: владелец видит детали своего курса"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.owner_client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Course')

    # ========== ТЕСТЫ ОБНОВЛЕНИЯ ==========

    def test_update_course_owner_success(self):
        """Тест: владелец может обновить свой курс"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.owner_client.patch(
            url, {'name': 'Updated Course'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Course')

    def test_update_course_other_user_forbidden(self):
        """Тест: другой пользователь не может обновить чужой курс"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.other_client.patch(
            url, {'name': 'Updated Course'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_course_moderator_success(self):
        """Тест: модератор может обновить любой курс"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.moderator_client.patch(
            url, {'name': 'Moderator Updated'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Moderator Updated')

    # ========== ТЕСТЫ УДАЛЕНИЯ ==========

    def test_delete_course_owner_success(self):
        """Тест: владелец может удалить свой курс"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.owner_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Course.objects.count(), 0)

    def test_delete_course_moderator_forbidden(self):
        """Тест: модератор не может удалить курс"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.moderator_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Course.objects.count(), 1)


class LessonTests(APITestCase):
    """Тесты для CRUD операций с уроками"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.owner = User.objects.create_user(
            email='owner@test.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123'
        )

        from django.contrib.auth.models import Group
        moderator_group, _ = Group.objects.get_or_create(name='Модераторы')
        self.moderator.groups.add(moderator_group)

        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            price=1000,
            owner=self.owner
        )

        self.lesson = Lesson.objects.create(
            name='Test Lesson',
            description='Test Description',
            video_url='https://www.youtube.com/watch?v=abc123',
            course=self.course,
            owner=self.owner
        )

        self.lesson_data = {
            'name': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://www.youtube.com/watch?v=xyz789',
            'course': self.course.id
        }

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

        self.moderator_client = APIClient()
        self.moderator_client.force_authenticate(user=self.moderator)

    # ========== ТЕСТЫ ВАЛИДАЦИИ YOUTUBE ==========

    def test_create_lesson_invalid_youtube_url(self):
        """Тест: невалидная YouTube ссылка не допускается"""
        invalid_data = self.lesson_data.copy()
        invalid_data['video_url'] = 'https://vimeo.com/123456'

        url = reverse('lesson-list-create')
        response = self.owner_client.post(url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)

    def test_create_lesson_valid_youtube_url_formats(self):
        """Тест: различные форматы YouTube ссылок допускаются"""
        valid_urls = [
            'https://www.youtube.com/watch?v=abc123def',
            'https://youtu.be/abc123def',
            'https://www.youtube.com/embed/abc123def',
            'https://www.youtube.com/shorts/abc123def'
        ]

        for url in valid_urls:
            test_data = self.lesson_data.copy()
            test_data['video_url'] = url

            response = self.owner_client.post(
                reverse('lesson-list-create'), test_data, format='json'
            )
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED,
                f'Failed for URL: {url}'
            )

    # ========== ТЕСТЫ СОЗДАНИЯ ==========

    def test_create_lesson_success(self):
        """Тест успешного создания урока владельцем"""
        url = reverse('lesson-list-create')
        response = self.owner_client.post(url, self.lesson_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)
        self.assertEqual(Lesson.objects.last().owner, self.owner)

    def test_create_lesson_moderator_forbidden(self):
        """Тест: модератор не может создавать уроки"""
        url = reverse('lesson-list-create')
        response = self.moderator_client.post(url, self.lesson_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ========== ТЕСТЫ ОБНОВЛЕНИЯ ==========

    def test_update_lesson_owner_success(self):
        """Тест: владелец может обновить свой урок"""
        url = reverse('lesson-detail', args=[self.lesson.id])
        response = self.owner_client.patch(
            url, {'name': 'Updated Lesson'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Lesson')

    def test_update_lesson_moderator_success(self):
        """Тест: модератор может обновить любой урок"""
        url = reverse('lesson-detail', args=[self.lesson.id])
        response = self.moderator_client.patch(
            url, {'name': 'Moderator Updated'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Moderator Updated')

    # ========== ТЕСТЫ УДАЛЕНИЯ ==========

    def test_delete_lesson_owner_success(self):
        """Тест: владелец может удалить свой урок"""
        url = reverse('lesson-detail', args=[self.lesson.id])
        response = self.owner_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_delete_lesson_moderator_forbidden(self):
        """Тест: модератор не может удалить урок"""
        url = reverse('lesson-detail', args=[self.lesson.id])
        response = self.moderator_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Lesson.objects.count(), 1)


class SubscriptionTests(APITestCase):
    """Тесты для функционала подписки на курс"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            price=1000
        )

        self.client.force_authenticate(user=self.user)

    def test_subscribe_to_course(self):
        """Тест: подписка на курс"""
        url = reverse('subscription')
        response = self.client.post(url, {'course_id': self.course.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Подписка добавлена')
        self.assertTrue(response.data['is_subscribed'])

        self.assertTrue(Subscription.objects.filter(
            user=self.user, course=self.course
        ).exists())

    def test_unsubscribe_from_course(self):
        """Тест: отписка от курса"""
        Subscription.objects.create(user=self.user, course=self.course)

        url = reverse('subscription')
        response = self.client.post(url, {'course_id': self.course.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Подписка удалена')
        self.assertFalse(response.data['is_subscribed'])

        self.assertFalse(Subscription.objects.filter(
            user=self.user, course=self.course
        ).exists())

    def test_subscribe_without_course_id(self):
        """Тест: подписка без указания course_id"""
        url = reverse('subscription')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course_id', str(response.data))

    def test_subscribe_to_nonexistent_course(self):
        """Тест: подписка на несуществующий курс"""
        url = reverse('subscription')
        response = self.client.post(url, {'course_id': 99999}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_subscription_list(self):
        """Тест: получение списка подписок пользователя"""
        course2 = Course.objects.create(name='Course 2', price=500)
        Subscription.objects.create(user=self.user, course=self.course)
        Subscription.objects.create(user=self.user, course=course2)

        url = reverse('subscription')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_course_serializer_has_is_subscribed(self):
        """Тест: сериализатор курса возвращает признак подписки"""
        Subscription.objects.create(user=self.user, course=self.course)

        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('is_subscribed' in response.data)
        self.assertTrue(response.data['is_subscribed'])


class PaginationTests(APITestCase):
    """Тесты для пагинации"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        # Создаем 25 курсов
        for i in range(25):
            Course.objects.create(
                name=f'Course {i}',
                description=f'Description {i}',
                owner=self.user
            )

    def test_course_pagination_default_page_size(self):
        """Тест: пагинация курсов (10 на странице по умолчанию)"""
        url = reverse('course-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['count'], 25)
        self.assertIsNotNone(response.data['next'])

    def test_course_pagination_custom_page_size(self):
        """Тест: пагинация с кастомным размером страницы"""
        url = reverse('course-list')
        response = self.client.get(url, {'page_size': 5}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_course_pagination_max_page_size_limit(self):
        """Тест: ограничение максимального размера страницы"""
        url = reverse('course-list')
        response = self.client.get(url, {'page_size': 100}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Максимальный размер 50, но всего 25 курсов
        self.assertEqual(len(response.data['results']), 25)


class LessonFilterTests(APITestCase):
    """Тесты для фильтрации уроков"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        self.course1 = Course.objects.create(
            name='Course 1', description='First course', owner=self.user
        )
        self.course2 = Course.objects.create(
            name='Course 2', description='Second course', owner=self.user
        )

        self.lesson1 = Lesson.objects.create(
            name='Lesson 1',
            description='First lesson',
            course=self.course1,
            owner=self.user
        )
        self.lesson2 = Lesson.objects.create(
            name='Lesson 2',
            description='Second lesson',
            course=self.course2,
            owner=self.user
        )

    def test_lessons_by_course_filter(self):
        """Тест: фильтрация уроков по курсу"""
        url = reverse('course-lessons', args=[self.course1.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Lesson 1')


class PermissionTests(APITestCase):
    """Тесты для прав доступа"""

    def setUp(self):
        self.regular_user = User.objects.create_user(
            email='regular@test.com',
            password='testpass123'
        )
        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123'
        )

        from django.contrib.auth.models import Group
        moderator_group, _ = Group.objects.get_or_create(name='Модераторы')
        self.moderator.groups.add(moderator_group)

        self.course = Course.objects.create(
            name='Test Course',
            owner=self.regular_user
        )

    def test_regular_user_cannot_create_course_if_moderator_group_only(self):
        """Тест: обычный пользователь может создавать курсы"""
        # Обычный пользователь НЕ является модератором, поэтому может создавать курсы
        client = APIClient()
        client.force_authenticate(user=self.regular_user)

        url = reverse('course-list')
        response = client.post(url, {'name': 'New Course'}, format='json')

        # Обычный пользователь может создавать курсы
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_moderator_cannot_create_course(self):
        """Тест: модератор не может создавать курсы"""
        client = APIClient()
        client.force_authenticate(user=self.moderator)

        url = reverse('course-list')
        response = client.post(url, {'name': 'Moderator Course'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CourseDetailViewTests(APITestCase):
    """Тесты для детального просмотра курса"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            price=1000
        )
        self.client.force_authenticate(user=self.user)

    def test_course_detail_returns_is_subscribed_false(self):
        """Тест: детали курса возвращают is_subscribed=False для неподписанного"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_subscribed'])

    def test_course_detail_has_lessons_count(self):
        """Тест: детали курса содержат количество уроков"""
        Lesson.objects.create(
            name='Lesson 1',
            course=self.course,
            owner=self.user
        )
        Lesson.objects.create(
            name='Lesson 2',
            course=self.course,
            owner=self.user
        )

        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lessons_count'], 2)

    def test_course_detail_has_lessons_list(self):
        """Тест: детали курса содержат список уроков"""
        Lesson.objects.create(
            name='Lesson 1',
            course=self.course,
            owner=self.user
        )

        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['lessons']), 1)
        self.assertEqual(response.data['lessons'][0]['name'], 'Lesson 1')