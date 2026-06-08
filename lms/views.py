from rest_framework import viewsets, generics, permissions, status
from lms.models import Course, Lesson, Subscription
from lms.serializers import (
    CourseSerializer, CourseCreateUpdateSerializer,
    LessonSerializer, LessonCreateUpdateSerializer,
    SubscriptionSerializer
)
from lms.paginators import CoursePaginator, LessonPaginator
from users.permissions import IsModerator, IsOwner
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from django.shortcuts import get_object_or_404
from django.conf import settings
from lms.models import Course, Payment
from lms.serializers import PaymentSerializer, PaymentCreateSerializer, PaymentStatusSerializer
from lms.services import (
    sync_course_with_stripe, create_checkout_session,
    get_stripe_session_status
)

class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet для CRUD операций с курсами
    """
    queryset = Course.objects.all()
    pagination_class = CoursePaginator  # Добавляем пагинацию

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer

    def get_serializer_context(self):
        """Передаем request в сериализатор для определения подписки"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        """Фильтрация списка курсов"""
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        if user.groups.filter(name='Модераторы').exists():
            return qs

        return qs.filter(owner=user)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, ~IsModerator]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [permissions.IsAuthenticated, IsOwner | IsModerator]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAuthenticated, IsOwner, ~IsModerator]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class LessonListCreateView(generics.ListCreateAPIView):
    """
    Generic класс для получения списка уроков и создания нового урока
    """
    queryset = Lesson.objects.select_related('course', 'owner').all()
    pagination_class = LessonPaginator  # Добавляем пагинацию

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LessonCreateUpdateSerializer
        return LessonSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated:
            return qs.none()

        if user.groups.filter(name='Модераторы').exists():
            return qs

        return qs.filter(owner=user)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), ~IsModerator()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
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
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), IsOwner() | IsModerator()]
        elif self.request.method == 'DELETE':
            return [permissions.IsAuthenticated(), IsOwner(), ~IsModerator()]
        return [permissions.IsAuthenticated()]


class LessonsByCourseView(generics.ListAPIView):
    """
    Список уроков по конкретному курсу
    """
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LessonPaginator  # Добавляем пагинацию

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        user = self.request.user

        qs = Lesson.objects.filter(course_id=course_id).select_related('course', 'owner')

        if user.groups.filter(name='Модераторы').exists():
            return qs

        return qs.filter(owner=user)


class SubscriptionView(APIView):
    """
    Эндпоинт для управления подпиской на курс
    POST /api/lms/subscribe/ - создать или удалить подписку
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {'error': 'Необходимо указать course_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = get_object_or_404(Course, pk=course_id)

        # Проверяем, есть ли уже подписка
        subscription = Subscription.objects.filter(user=user, course=course)

        if subscription.exists():
            # Если подписка есть - удаляем
            subscription.delete()
            message = 'Подписка удалена'
            subscribed = False
        else:
            # Если подписки нет - создаем
            Subscription.objects.create(user=user, course=course)
            message = 'Подписка добавлена'
            subscribed = True

        return Response({
            'message': message,
            'is_subscribed': subscribed,
            'course_id': course.id,
            'course_name': course.name
        }, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """
        Получение списка подписок пользователя
        """
        subscriptions = Subscription.objects.filter(user=request.user).select_related('course')
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)


class CoursePaymentView(APIView):
    """
    Эндпоинт для оплаты курса через Stripe
    POST /api/lms/courses/{id}/payment/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        course = get_object_or_404(Course, pk=pk)

        # Проверяем цену курса
        if course.price <= 0:
            return Response(
                {'error': 'У данного курса нет установленной цены'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Синхронизируем курс с Stripe
        try:
            course = sync_course_with_stripe(course)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Создаем сессию для оплаты
        success_url = request.data.get(
            'success_url',
            'http://localhost:3000/success'
        )
        cancel_url = request.data.get(
            'cancel_url',
            'http://localhost:3000/cancel'
        )

        try:
            checkout_session = create_checkout_session(
                price_id=course.stripe_price_id,
                course_name=course.name,
                success_url=success_url,
                cancel_url=cancel_url
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Создаем запись о платеже
        payment = Payment.objects.create(
            user=request.user,
            course=course,
            amount=course.price,
            stripe_session_id=checkout_session.id,
            stripe_payment_intent_id=checkout_session.payment_intent,
            payment_url=checkout_session.url,
            status='pending'
        )

        return Response({
            'payment_id': payment.id,
            'payment_url': checkout_session.url,
            'session_id': checkout_session.id,
        }, status=status.HTTP_201_CREATED)


class PaymentStatusView(APIView):
    """
    Эндпоинт для проверки статуса платежа
    GET /api/lms/payments/{id}/status/
    POST /api/lms/payments/status/ - по session_id
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        """Получение статуса платежа по ID в БД"""
        payment = get_object_or_404(Payment, pk=pk, user=request.user)

        # Дополнительное задание: проверка статуса через Stripe
        if payment.stripe_session_id:
            try:
                session = get_stripe_session_status(payment.stripe_session_id)

                # Обновляем статус платежа
                if session.payment_status == 'paid' and payment.status != 'paid':
                    payment.status = 'paid'
                    payment.paid_at = payment.paid_at or session.created
                    payment.save()
                elif session.payment_status == 'unpaid' and payment.status == 'pending':
                    payment.status = 'pending'
                    payment.save()
                elif session.status == 'expired':
                    payment.status = 'failed'
                    payment.save()
            except Exception:
                pass

        serializer = PaymentSerializer(payment)
        return Response(serializer.data)

    def post(self, request):
        """Проверка статуса платежа по session_id из Stripe"""
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data['session_id']

        try:
            payment = Payment.objects.get(stripe_session_id=session_id, user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Платеж не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Получаем статус из Stripe
        try:
            session = get_stripe_session_status(session_id)

            # Обновляем статус платежа
            if session.payment_status == 'paid':
                payment.status = 'paid'
                payment.paid_at = payment.paid_at or session.created
                payment.save()
            elif session.status == 'expired':
                payment.status = 'failed'
                payment.save()

            return Response({
                'payment_id': payment.id,
                'status': payment.status,
                'stripe_status': session.payment_status,
                'session_status': session.status
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentListView(APIView):
    """
    Список платежей пользователя
    GET /api/lms/payments/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).select_related('course')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)