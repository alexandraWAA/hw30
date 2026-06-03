from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from users.models import User, Payment
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer,
    PaymentSerializer, PaymentCreateSerializer, UserWithPaymentsSerializer
)


class UserViewSet(viewsets.ModelViewSet):
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
        user = self.get_object()
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='payments')
    def payments(self, request, pk=None):
        user = self.get_object()
        serializer = UserWithPaymentsSerializer(user)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('user', 'course', 'lesson').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentCreateSerializer
        return PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)

        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)

        payment_method = self.request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        ordering = self.request.query_params.get('ordering', '-payment_date')
        if ordering in ['payment_date', '-payment_date']:
            queryset = queryset.order_by(ordering)

        return queryset