from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import AuthorProfile, UserAccount

admin.site.unregister(User)


class AuthorProfileInline(admin.StackedInline):
    model = AuthorProfile
    can_delete = False


class UserAccountInline(admin.StackedInline):
    model = UserAccount
    can_delete = False
    fields = ["platform_role", "stripe_customer_id"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserAccountInline, AuthorProfileInline]


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "created_at"]
    search_fields = ["display_name", "user__username"]


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "platform_role", "stripe_customer_id", "updated_at"]
    list_filter = ["platform_role"]
    search_fields = ["user__username", "user__email", "stripe_customer_id"]
