from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action
from users.models import User
from users.serializers import (
    UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=['patch', 'put'], url_path='profile')
    def update_profile(self, request, pk=None):
        """
        Дополнительное задание: эндпоинт для редактирования профиля пользователя
        """
        user = self.get_object()
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)