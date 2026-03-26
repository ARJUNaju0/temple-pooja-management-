from rest_framework.permissions import BasePermission


class IsAdminOrOperator(BasePermission):
    """
    Allows access only to admin / staff / temple_admin users
    """

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (user.is_staff or getattr(user, 'role', None) in ['admin', 'temple_admin'])
        )
