from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)


class IsStaffUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == "staff"))


class HasPermissionCode(BasePermission):
    code = ""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if not (user.is_staff or getattr(user, "user_type", "") == "staff"):
            return False
        code = self._resolve_code(request, view)
        if not code:
            return True
        return user.has_perm_code(code)

    def _resolve_code(self, request, view):
        perm_map = getattr(view, "permission_map", None) or {}
        action = getattr(view, "action", None)
        if action and action in perm_map:
            return perm_map[action]
        if request.method in perm_map:
            return perm_map[request.method]
        return getattr(view, "permission_code", None) or self.code


def permission_code(code: str):
    class _Perm(HasPermissionCode):
        def has_permission(self, request, view):
            user = request.user
            if not user or not user.is_authenticated:
                return False
            if user.is_superuser:
                return True
            if not (user.is_staff or getattr(user, "user_type", "") == "staff"):
                return False
            return user.has_perm_code(code)

    _Perm.__name__ = f"Has_{code.replace('.', '_')}"
    return _Perm


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        owner = getattr(obj, "user", None)
        return owner == user


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
