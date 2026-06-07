from rest_framework import viewsets, generics, permissions
from rest_framework.exceptions import PermissionDenied
from lms.models import Course, Lesson
from lms.serializers import (
    CourseSerializer, CourseCreateUpdateSerializer,
    LessonSerializer, LessonCreateUpdateSerializer
)
from users.permissions import IsModerator, IsOwner


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с курсами
    """
    queryset = Course.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer

    def get_queryset(self):
        """
        Фильтрация queryset для списка курсов:
        - Модераторы видят все курсы
        - Обычные пользователи видят только свои курсы
        """
        qs = super().get_queryset()
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return qs.none()

        # Модераторы видят все курсы
        if user.groups.filter(name='Модераторы').exists():
            return qs

        # Обычные пользователи видят только свои курсы
        return qs.filter(owner=user)

    def get_permissions(self):
        """
        Настройка прав доступа для разных действий
        """
        if self.action in ['list', 'retrieve']:
            # Просмотр списка и деталей доступен всем авторизованным
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'create':
            # Создание курса: только не-модераторы (обычные пользователи)
            permission_classes = [permissions.IsAuthenticated, ~IsModerator]
        elif self.action in ['update', 'partial_update']:
            # Редактирование: сначала проверяем владельца, потом модератора
            # (оптимизация: не делаем лишний запрос к БД)
            permission_classes = [permissions.IsAuthenticated, IsOwner | IsModerator]
        elif self.action == 'destroy':
            # Удаление: только владельцы (модераторы НЕ могут удалять)
            permission_classes = [permissions.IsAuthenticated, IsOwner, ~IsModerator]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """
        При создании курса автоматически назначаем владельца
        """
        serializer.save(owner=self.request.user)


class LessonListCreateView(generics.ListCreateAPIView):
    """
    Generic класс для получения списка уроков и создания нового урока
    """
    queryset = Lesson.objects.select_related('course', 'owner').all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LessonCreateUpdateSerializer
        return LessonSerializer

    def get_queryset(self):
        """
        Фильтрация queryset для списка уроков:
        - Модераторы видят все уроки
        - Обычные пользователи видят только свои уроки
        """
        qs = super().get_queryset()
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return qs.none()

        # Модераторы видят все уроки
        if user.groups.filter(name='Модераторы').exists():
            return qs

        # Обычные пользователи видят только свои уроки
        return qs.filter(owner=user)

    def get_permissions(self):
        """
        Настройка прав доступа
        Достаточно проверять только на POST, на все остальное - только аутентификация
        """
        if self.request.method == 'POST':
            # Создание урока: только не-модераторы (обычные пользователи)
            return [permissions.IsAuthenticated(), ~IsModerator()]
        # GET и другие методы: только проверка аутентификации
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """
        При создании урока автоматически назначаем владельца
        """
        serializer.save(owner=self.request.user)


class LessonRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Generic класс для получения, обновления и удаления одного урока
    """
    queryset = Lesson.objects.select_related('course', 'owner').all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return LessonCreateUpdateSerializer
        return LessonSerializer

    def get_permissions(self):
        """
        Настройка прав доступа для разных действий
        """
        if self.request.method == 'GET':
            # Просмотр деталей доступен всем авторизованным
            return [permissions.IsAuthenticated()]
        elif self.request.method in ['PUT', 'PATCH']:
            # Редактирование: сначала проверяем владельца, потом модератора
            return [permissions.IsAuthenticated(), IsOwner() | IsModerator()]
        elif self.request.method == 'DELETE':
            # Удаление: только владельцы (модераторы НЕ могут удалять)
            return [permissions.IsAuthenticated(), IsOwner(), ~IsModerator()]
        return [permissions.IsAuthenticated()]


class LessonsByCourseView(generics.ListAPIView):
    """
    Список уроков по конкретному курсу
    """
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Фильтрация уроков по курсу с учетом прав пользователя
        """
        course_id = self.kwargs.get('course_id')
        user = self.request.user

        # Базовый queryset для указанного курса
        qs = Lesson.objects.filter(course_id=course_id).select_related('course', 'owner')

        # Модераторы видят все уроки курса
        if user.groups.filter(name='Модераторы').exists():
            return qs

        # Обычные пользователи видят только свои уроки в этом курсе
        return qs.filter(owner=user)