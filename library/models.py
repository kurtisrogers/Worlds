"""Reader library models — saved books and author follows."""

from django.conf import settings
from django.db import models


class SavedStory(models.Model):
    """A story saved to a reader's personal collection."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_stories",
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="saved_by",
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_at"]
        unique_together = [("user", "story")]

    def __str__(self) -> str:
        return f"{self.user.username} saved {self.story.title}"


class AuthorFollow(models.Model):
    """A reader following an author for updates."""

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="followers",
    )
    followed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-followed_at"]
        unique_together = [("follower", "author")]

    def __str__(self) -> str:
        return f"{self.follower.username} follows {self.author.username}"
