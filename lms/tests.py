from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from lms.models import Course, Lesson, Subscription
from users.models import User

User = get_user_model()


class LessonTests(APITestCase):
    """
    Тесты для CRUD операций с уроками
    """

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

        # Создаем группу модераторов и добавляем пользователя
        from django.contrib.auth.models import Group
        moderator_group, _ = Group.objects.get_or_create(name='Модераторы')
        self.moderator.groups.add(moderator_group)

        # Создаем курс
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            owner=self.owner
        )

        # Данные для урока
        self.lesson_data = {
            'name': 'Test Lesson',
            'description': 'Test Lesson Description',
            'video_url': 'https://www.youtube.com/watch?v=abc123',
            'course': self.course.id
        }

        # Аутентифицируем клиенты
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

        self.moderator_client = APIClient()
        self.moderator_client.force_authenticate(user=self.moderator)

    # ========== ТЕСТЫ СОЗДАНИЯ ==========

    def test_create_lesson_success(self):
        """Тест успешного создания урока владельцем"""
        url = reverse('lesson-list-create')
        response = self.owner_client.post(url, self.lesson_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 1)
        self.assertEqual(Lesson.objects.first().name, 'Test Lesson')
        self.assertEqual(Lesson.objects.first().owner, self.owner)

    def test_create_lesson_unauthorized(self):
        """Тест создания урока неавторизованным пользователем"""
        client = APIClient()
        url = reverse('lesson-list-create')
        response = client.post(url, self.lesson_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_lesson_moderator_forbidden(self):
        """Тест: модератор не может создавать уроки"""
        url = reverse('lesson-list-create')
        response = self.moderator_client.post(url, self.lesson_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_lesson_invalid_youtube_url(self):
        """Тест: невалидная YouTube ссылка не допускается"""
        invalid_data = self.lesson_data.copy()
        invalid_data['video_url'] = 'https://vimeo.com/123456'

        url = reverse('lesson-list-create')
        response = self.owner_client.post(url, invalid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('video_url', response.data)
        self.assertIn('YouTube', str(response.data['video_url']))

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

            response = self.owner_client.post(reverse('lesson-list-create'), test_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, f'Failed for URL: {url}')

    # ========== ТЕСТЫ ПОЛУЧЕНИЯ ==========

    def test_get_lesson_list_owner(self):
        """Тест: владелец видит свои уроки"""
        # Создаем урок
        Lesson.objects.create(
            name='Owner Lesson',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-list-create')
        response = self.owner_client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_lesson_list_moderator_sees_all(self):
        """Тест: модератор видит все уроки"""
        # Создаем урок от имени владельца
        Lesson.objects.create(
            name='Owner Lesson',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-list-create')
        response = self.moderator_client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    # ========== ТЕСТЫ ОБНОВЛЕНИЯ ==========

    def test_update_lesson_owner_success(self):
        """Тест: владелец может обновить свой урок"""
        lesson = Lesson.objects.create(
            name='Original Name',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-detail', args=[lesson.id])
        response = self.owner_client.patch(url, {'name': 'Updated Name'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Name')

    def test_update_lesson_other_user_forbidden(self):
        """Тест: другой пользователь не может обновить чужой урок"""
        lesson = Lesson.objects.create(
            name='Original Name',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-detail', args=[lesson.id])
        response = self.other_client.patch(url, {'name': 'Updated Name'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_lesson_moderator_success(self):
        """Тест: модератор может обновить любой урок"""
        lesson = Lesson.objects.create(
            name='Original Name',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-detail', args=[lesson.id])
        response = self.moderator_client.patch(url, {'name': 'Moderator Updated'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Moderator Updated')

    # ========== ТЕСТЫ УДАЛЕНИЯ ==========

    def test_delete_lesson_owner_success(self):
        """Тест: владелец может удалить свой урок"""
        lesson = Lesson.objects.create(
            name='To Delete',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-detail', args=[lesson.id])
        response = self.owner_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Lesson.objects.count(), 0)

    def test_delete_lesson_moderator_forbidden(self):
        """Тест: модератор не может удалить урок"""
        lesson = Lesson.objects.create(
            name='To Delete',
            description='Description',
            video_url='https://www.youtube.com/watch?v=test',
            course=self.course,
            owner=self.owner
        )

        url = reverse('lesson-detail', args=[lesson.id])
        response = self.moderator_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Lesson.objects.count(), 1)


class SubscriptionTests(APITestCase):
    """
    Тесты для функционала подписки на курс
    """

    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description'
        )

        self.client.force_authenticate(user=self.user)

    def test_subscribe_to_course(self):
        """Тест: подписка на курс"""
        url = reverse('subscription')
        response = self.client.post(url, {'course_id': self.course.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Подписка добавлена')
        self.assertTrue(response.data['is_subscribed'])

        # Проверяем, что подписка создана в БД
        self.assertTrue(Subscription.objects.filter(user=self.user, course=self.course).exists())

    def test_unsubscribe_from_course(self):
        """Тест: отписка от курса"""
        # Сначала подписываемся
        Subscription.objects.create(user=self.user, course=self.course)

        url = reverse('subscription')
        response = self.client.post(url, {'course_id': self.course.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Подписка удалена')
        self.assertFalse(response.data['is_subscribed'])

        # Проверяем, что подписка удалена из БД
        self.assertFalse(Subscription.objects.filter(user=self.user, course=self.course).exists())

    def test_subscribe_without_course_id(self):
        """Тест: подписка без указания course_id"""
        url = reverse('subscription')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course_id', response.data['error'])

    def test_subscribe_to_nonexistent_course(self):
        """Тест: подписка на несуществующий курс"""
        url = reverse('subscription')
        response = self.client.post(url, {'course_id': 99999}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_subscription_list(self):
        """Тест: получение списка подписок пользователя"""
        # Создаем несколько подписок
        course2 = Course.objects.create(name='Course 2', description='Second Course')
        Subscription.objects.create(user=self.user, course=self.course)
        Subscription.objects.create(user=self.user, course=course2)

        url = reverse('subscription')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_course_serializer_has_is_subscribed_field(self):
        """Тест: сериализатор курса возвращает признак подписки"""
        # Подписываемся на курс
        Subscription.objects.create(user=self.user, course=self.course)

        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('is_subscribed' in response.data)
        self.assertTrue(response.data['is_subscribed'])

    def test_course_serializer_is_subscribed_false(self):
        """Тест: сериализатор курса - не подписан"""
        url = reverse('course-detail', args=[self.course.id])
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_subscribed'])


class PaginationTests(APITestCase):
    """
    Тесты для пагинации
    """

    def setUp(self):
        """Создаем несколько курсов для проверки пагинации"""
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

    def test_course_pagination_default(self):
        """Тест: пагинация курсов по умолчанию (10 на странице)"""
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

    def test_course_pagination_max_page_size(self):
        """Тест: пагинация - ограничение максимального размера страницы"""
        url = reverse('course-list')
        response = self.client.get(url, {'page_size': 100}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Максимальный размер 50, поэтому должно быть 25
        self.assertEqual(len(response.data['results']), 25)