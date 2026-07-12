"""Template context for user roles."""

from accounts.roles import get_user_account, user_has_role
from accounts.models import PlatformRole


def user_roles(request):
    account = get_user_account(request.user) if request.user.is_authenticated else None
    return {
        "user_account": account,
        "is_staff_member": user_has_role(request.user, PlatformRole.SUPPORT),
        "can_moderate": user_has_role(request.user, PlatformRole.MODERATOR),
        "is_super_admin": user_has_role(request.user, PlatformRole.SUPER_ADMIN),
    }
