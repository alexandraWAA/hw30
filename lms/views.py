import string

from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from lms.models import Course, Lesson, Subscription, Payment
from lms.serializers import (
    CourseSerializer, CourseCreateUpdateSerializer,
    LessonSerializer, LessonCreateUpdateSerializer,
    SubscriptionSerializer, PaymentSerializer
)
from lms.paginators import CoursePaginator, LessonPaginator
from lms.services import sync_course_with_stripe, create_checkout_session, get_stripe_session_status
from users.permissions import IsModerator, IsOwner


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для управления курсами"""
    queryset = Course.objects.all()
    pagination_class = CoursePaginator

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseCreateUpdateSerializer
        return CourseSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
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
    """Список и создание уроков"""
    queryset = Lesson.objects.select_related('course', 'owner').all()
    pagination_class = LessonPaginator

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
    """Получение, обновление и удаление урока"""
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
    """Список уроков по конкретному курсу"""
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LessonPaginator

    def get_queryset(self):
        course_id = self.kwargs.get('course_id')
        user = self.request.user
        qs = Lesson.objects.filter(course_id=course_id).select_related('course', 'owner')
        if user.groups.filter(name='Модераторы').exists():
            return qs
        return qs.filter(owner=user)


# ============================================
# APIView с полной документацией
# ============================================

@extend_schema_view(
    post=extend_schema(
        summary="Управление подпиской на курс",
        description="Создает или удаляет подписку на курс. Если подписка существует - удаляет, если нет - создает.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'course_id': {'type': 'integer', 'description': 'ID курса', 'example': 1}
                },
                'required': ['course_id']
            }
        },
        responses={
            200: OpenApiResponse(
                description='Успешный ответ',
                response={
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string', 'example': 'Подписка добавлена'},
                        'is_subscribed': {'type': 'boolean', 'example': True},
                        'course_id': {'type': 'integer', 'example': 1},
                        'course_name': {'type': 'string', 'example': 'Python Course'}
                    }
                }
            ),
            400: OpenApiResponse(description='Не указан course_id'),
            404: OpenApiResponse(description='Курс не найден'),
        },
        tags=['Подписки']
    ),
    get=extend_schema(
        summary="Список подписок пользователя",
        description="Возвращает список всех подписок текущего пользователя.",
        responses={200: SubscriptionSerializer(many=True)},
        tags=['Подписки']
    )
)
class SubscriptionView(APIView):
    """Эндпоинт для управления подпиской на курс"""
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
        subscription = Subscription.objects.filter(user=user, course=course)

        if subscription.exists():
            subscription.delete()
            message = 'Подписка удалена'
            subscribed = False
        else:
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
        subscriptions = Subscription.objects.filter(user=request.user).select_related('course')
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)


@extend_schema_view(
    post=extend_schema(
        summary="Создание платежа для курса",
        description="Создает платеж в Stripe и возвращает ссылку на оплату. Для тестирования используйте тестовые карты Stripe.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'success_url': {'type': 'string', 'description': 'URL для перенаправления после успешной оплаты',
                                    'example': 'http://localhost:8000/api/docs/'},
                    'cancel_url': {'type': string', 'description': 'URL для перенаправления при отмене оплаты', '
                                   example': 'http: // localhost

:8000 / api / docs / '}
}
}
},
responses = {
    201: OpenApiResponse(
        description='Платеж успешно создан',
        response={
            'type': 'object',
            'properties': {
                'payment_id': {'type': 'integer', 'example': 1},
                'payment_url': {'type': 'string', 'example': 'https://checkout.stripe.com/...'},
                'session_id': {'type': 'string', 'example': 'cs_test_...'}
            }
        }
    ),
    400: OpenApiResponse(description='У курса нет цены'),
    404: OpenApiResponse(description='Курс не найден'),
    500: OpenApiResponse(description='Ошибка Stripe'),
},
tags = ['Платежи']
)
)

class CoursePaymentView(APIView):
    """Эндпоинт для оплаты курса через Stripe"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        course = get_object_or_404(Course, pk=pk)

        if course.price <= 0:
            return Response(
                {'error': 'У данного курса нет установленной цены'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            course = sync_course_with_stripe(course)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        success_url = request.data.get(
            'success_url',
            'http://localhost:8000/api/docs/'
        )
        cancel_url = request.data.get(
            'cancel_url',
            'http://localhost:8000/api/docs/'
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


@extend_schema_view(
    get=extend_schema(
        summary="Получение статуса платежа по ID",
        description="Возвращает статус платежа по ID платежа в базе данных. При необходимости обновляет статус через Stripe.",
        responses={
            200: PaymentSerializer,
            404: OpenApiResponse(description='Платеж не найден'),
        },
        tags=['Платежи']
    ),
    post=extend_schema(
        summary="Проверка статуса платежа по session_id Stripe",
        description="Проверяет статус платежа в Stripe по session_id и обновляет статус в базе данных.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'session_id': {'type': 'string', 'description': 'ID сессии Stripe', 'example': 'cs_test_...'}
                },
                'required': ['session_id']
            }
        },
        responses={
            200: OpenApiResponse(
                description='Статус платежа',
                response={
                    'type': 'object',
                    'properties': {
                        'payment_id': {'type': 'integer', 'example': 1},
                        'status': {'type': 'string', 'enum': ['pending', 'paid', 'failed', 'refunded']},
                        'stripe_status': {'type': 'string', 'example': 'paid'},
                        'session_status': {'type': 'string', 'example': 'complete'}
                    }
                }
            ),
            404: OpenApiResponse(description='Платеж не найден'),
            500: OpenApiResponse(description='Ошибка Stripe'),
        },
        tags=['Платежи']
    )
)
class PaymentStatusView(APIView):
    """Эндпоинт для проверки статуса платежа"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        payment = get_object_or_404(Payment, pk=pk, user=request.user)

        if payment.stripe_session_id:
            try:
                session = get_stripe_session_status(payment.stripe_session_id)
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
        session_id = request.data.get('session_id')

        if not session_id:
            return Response(
                {'error': 'Необходимо указать session_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment = Payment.objects.get(stripe_session_id=session_id, user=request.user)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Платеж не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            session = get_stripe_session_status(session_id)

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


@extend_schema_view(
    get=extend_schema(
        summary="Список платежей пользователя",
        description="Возвращает список всех платежей текущего пользователя.",
        responses={200: PaymentSerializer(many=True)},
        tags=['Платежи']
    )
)
class PaymentListView(APIView):
    """Список платежей пользователя"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payments = Payment.objects.filter(user=request.user).select_related('course')
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)