from rest_framework import viewsets, generics, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, NumberFilter, DateFilter, OrderingFilter
from users.models import User, Payment
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer,
    PaymentSerializer, PaymentCreateSerializer, UserWithPaymentsSerializer
)


class PaymentFilter(FilterSet):
    """
    Фильтрация для платежей
    Задание 4: фильтрация по курсу, уроку, способу оплаты и сортировка по дате
    """
    course = NumberFilter(field_name='course__id')
    lesson = NumberFilter(field_name='lesson__id')
    payment_method = CharFilter(field_name='payment_method')

    # Сортировка по дате оплаты
    ordering = OrderingFilter(
        fields=(
            ('payment_date', 'payment_date'),
        ),
        field_labels={
            'payment_date': 'Дата оплаты',
        }
    )

    class Meta:
        model = Payment
        fields = ['course', 'lesson', 'payment_method', 'ordering']


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'payments':
            return UserWithPaymentsSerializer
        return UserSerializer

    @action(detail=True, methods=['patch', 'put'], url_path='profile')
    def update_profile(self, request, pk=None):
        """
        Эндпоинт для редактирования профиля пользователя
        """
        user = self.get_object()
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        """
        * Дополнительное задание: вывод истории платежей пользователя
        """
        user = self.get_object()
        serializer = UserWithPaymentsSerializer(user)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления платежами с фильтрацией
    """
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        """
        Применяем фильтрацию к queryset
        """
        queryset = super().get_queryset()

        # Задание 4: фильтрация по параметрам запроса
        # Фильтр по курсу (передается в query параметре)
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        # Фильтр по уроку
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)

        # Фильтр по способу оплаты
        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Сортировка по дате оплаты
        ordering = self.request.query_params.get('ordering', '-payment_date')
        if ordering in ['payment_date', '-payment_date']:
            queryset = queryset.order_by(ordering)

        return queryset