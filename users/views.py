from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from users.models import User, Payment
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer,
    PaymentSerializer, PaymentCreateSerializer, UserWithPaymentsSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями
    """
    queryset = User.objects.all()

    def get_permissions(self):
        """
        Настройка прав доступа для разных действий
        """
        if self.action == 'create':
            # Регистрация доступна всем (неавторизованным)
            permission_classes = [permissions.AllowAny]
        elif self.action in ['retrieve', 'list']:
            # Просмотр профилей доступен авторизованным пользователям
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Редактирование и удаление только для своего профиля или админа
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'payments':
            return UserWithPaymentsSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        """
        Проверка, что пользователь редактирует свой профиль
        """
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Вы можете редактировать только свой профиль'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Проверка, что пользователь удаляет свой профиль
        """
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Вы можете удалить только свой профиль'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['patch', 'put'], url_path='profile')
    def update_profile(self, request, pk=None):
        """
        Эндпоинт для редактирования профиля пользователя
        """
        user = self.get_object()

        # Проверка, что пользователь редактирует свой профиль
        if user != request.user:
            return Response(
                {'error': 'Вы можете редактировать только свой профиль'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        """
        Вывод истории платежей пользователя
        """
        user = self.get_object()

        # * Дополнительное задание: ограничение просмотра чужого профиля
        if user != request.user and not request.user.is_staff:
            # Для чужого профиля возвращаем только общую информацию (без истории платежей)
            serializer = UserSerializer(user)
        else:
            serializer = UserWithPaymentsSerializer(user)

        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления платежами с фильтрацией
    """
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['course', 'lesson', 'payment_method']
    ordering_fields = ['payment_date']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        """
        Ограничиваем видимость платежей для обычных пользователей
        """
        queryset = super().get_queryset()
        user = self.request.user

        # Модераторы и администраторы видят все платежи
        if user.has_perm('users.can_view_all_payments') or user.is_staff:
            return queryset

        # Обычные пользователи видят только свои платежи
        return queryset.filter(user=user)