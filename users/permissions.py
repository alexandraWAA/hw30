from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Проверка, что пользователь является владельцем объекта
    """

    def has_object_permission(self, request, view, obj):
        # Проверяем, есть ли у объекта поле owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False

    def has_permission(self, request, view):
        """
        Для списков эта проверка не применяется,
        фильтрация происходит в get_queryset
        """
        return True


class IsModerator(permissions.BasePermission):
    """
    Проверка, что пользователь входит в группу модераторов
    """

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Модераторы').exists()

    def has_object_permission(self, request, view, obj):
        # Для объектов права те же, что и для списка
        return self.has_permission(request, view)


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешает полный доступ только администраторам,
    остальным только чтение
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешает редактирование только владельцу объекта,
    остальным только чтение
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user