from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import AuthorProfile

admin.site.unregister(User)


class AuthorProfileInline(admin.StackedInline):
    model = AuthorProfile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [AuthorProfileInline]


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "created_at"]
    search_fields = ["display_name", "user__username"]
