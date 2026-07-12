"""Account models — profiles, roles, and billing identifiers."""

from django.conf import settings
from django.db import models


class PlatformRole(models.TextChoices):
    READER = "reader", "Reader"
    SUPPORT = "support", "Support"
    MODERATOR = "moderator", "Moderator"
    SUPER_ADMIN = "super_admin", "Super Admin"


ROLE_RANK = {
    PlatformRole.READER: 0,
    PlatformRole.SUPPORT: 1,
    PlatformRole.MODERATOR: 2,
    PlatformRole.SUPER_ADMIN: 3,
}


class UserAccount(models.Model):
    """Extended account settings for all platform users."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="account",
    )
    platform_role = models.CharField(
        max_length=20,
        choices=PlatformRole.choices,
        default=PlatformRole.READER,
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_platform_role_display()})"

    @property
    def is_staff_member(self) -> bool:
        return ROLE_RANK.get(self.platform_role, 0) >= ROLE_RANK[PlatformRole.SUPPORT]

    @property
    def can_moderate(self) -> bool:
        return ROLE_RANK.get(self.platform_role, 0) >= ROLE_RANK[PlatformRole.MODERATOR]

    @property
    def is_super_admin(self) -> bool:
        return self.platform_role == PlatformRole.SUPER_ADMIN


class AuthorProfile(models.Model):
    """Extended profile for authors on the platform."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="author_profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    stripe_account_id = models.CharField(max_length=255, blank=True)
    stripe_connect_onboarded = models.BooleanField(default=False)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name or self.user.username

    @property
    def name(self) -> str:
        return self.display_name or self.user.get_full_name() or self.user.username
