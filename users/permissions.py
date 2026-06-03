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


class IsModerator(permissions.BasePermission):
    """
    Проверка, что пользователь входит в группу модераторов
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name='Модераторы').exists()


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