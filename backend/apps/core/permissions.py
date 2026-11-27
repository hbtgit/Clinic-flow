from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Role

MANAGERS = (Role.CLINIC_MANAGER, Role.TENANT_ADMIN)
FRONT_DESK = (Role.RECEPTIONIST, *MANAGERS)
CLINIC_STAFF = (Role.PRACTITIONER, *FRONT_DESK)


class IsClinicStaff(BasePermission):
    """Signed-in staff who belong to a clinic. Platform support is deliberately excluded."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.clinic_id and user.has_role(*CLINIC_STAFF)
        )


def roles_can_write(*roles):
    """Any clinic staff may read; only the given roles may create, change or delete."""

    class _RoleWrite(IsClinicStaff):
        def has_permission(self, request, view):
            if not super().has_permission(request, view):
                return False
            return request.method in SAFE_METHODS or request.user.has_role(*roles)

    _RoleWrite.__name__ = f"CanWrite_{'_'.join(roles)}"
    return _RoleWrite
