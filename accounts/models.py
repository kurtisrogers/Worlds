"""Account and author profile models."""

from django.conf import settings
from django.db import models


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
