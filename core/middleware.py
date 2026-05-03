from django.shortcuts import redirect
from django.urls import reverse


class RoleSelectionMiddleware:
    """
    Intercepts authenticated users who haven't completed role selection
    and redirects them to the role selection page. Allows access to
    auth-related URLs, admin, and the role selection page itself.
    """

    EXEMPT_PREFIXES = (
        '/accounts/',
        '/admin/',
        '/media/',
        '/static/',
    )
    USER_ADMIN_ALLOWED_PATHS = (
        '/dashboard/',
        '/role-management/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and not request.user.profile.setup_complete
            and not request.user.is_superuser
            and not self._is_exempt(request.path)
        ):
            return redirect('role_select')

        if (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.is_user_admin
            and not request.user.is_superuser
            and not self._is_user_admin_allowed(request.path)
        ):
            return redirect('user_role_management')

        return self.get_response(request)

    def _is_exempt(self, path):
        role_select_url = reverse('role_select')
        if path == role_select_url:
            return True
        return any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES)

    def _is_user_admin_allowed(self, path):
        if self._is_exempt(path):
            return True
        return any(path.startswith(prefix) for prefix in self.USER_ADMIN_ALLOWED_PATHS)
