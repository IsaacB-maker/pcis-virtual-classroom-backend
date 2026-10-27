
from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Only the authenticated Django superuser may manage
    school administrator accounts and their permissions.
    """

    message = "Only the school system owner can perform this action."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )


class IsSchoolAdministrator(BasePermission):
    """
    Allows authenticated staff administrators who are not
    superusers. Individual operations must also check the
    specific Django model permission they require.
    """

    message = "An authorized school administrator account is required."

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
            and not user.is_superuser
        )
