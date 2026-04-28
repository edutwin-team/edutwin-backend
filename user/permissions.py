from rest_framework.permissions import BasePermission
from .models import Role
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Role


class IsAdminOrTeacherOrReadOnly(BasePermission):
    """Lecture pour tous, écriture admin/teacher uniquement."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role in [
            Role.admin,
            Role.teacher,
        ]


class IsOwnerOrAdmin(BasePermission):
    """Teacher ne peut modifier que son propre contenu."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == Role.admin:
            return True
        return obj.created_by == request.user
