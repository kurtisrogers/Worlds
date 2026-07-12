"""Platform role helpers and decorators."""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from accounts.models import ROLE_RANK, PlatformRole, UserAccount


def get_user_account(user) -> UserAccount | None:
    if not user.is_authenticated:
        return None
    account, _ = UserAccount.objects.get_or_create(user=user)
    return account


def user_has_role(user, minimum_role: PlatformRole) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    account = get_user_account(user)
    if not account:
        return False
    return ROLE_RANK.get(account.platform_role, 0) >= ROLE_RANK[minimum_role]


def sync_django_staff_flags(user) -> None:
    """Keep Django admin flags aligned with platform role."""
    account = get_user_account(user)
    if not account:
        return
    changed = False
    if account.platform_role == PlatformRole.SUPER_ADMIN:
        if not user.is_superuser or not user.is_staff:
            user.is_superuser = True
            user.is_staff = True
            changed = True
    elif account.is_staff_member:
        if not user.is_staff or user.is_superuser:
            user.is_staff = True
            user.is_superuser = False
            changed = True
    else:
        if user.is_staff or user.is_superuser:
            user.is_staff = False
            user.is_superuser = False
            changed = True
    if changed:
        user.save(update_fields=["is_staff", "is_superuser"])


def role_required(minimum_role: PlatformRole):
    """Decorator requiring a minimum platform role."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if user_has_role(request.user, minimum_role):
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that area.")
            return redirect("stories:home")

        return wrapper

    return decorator
