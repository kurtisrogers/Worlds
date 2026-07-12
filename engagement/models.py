"""Engagement models — comments and reactions on chapters."""

from django.conf import settings
from django.db import models

from stories.models import Chapter


class ReactionType(models.TextChoices):
    LIKE = "like", "👍 Like"
    LOVE = "love", "❤️ Love"
    INSIGHTFUL = "insightful", "💡 Insightful"
    FIRE = "fire", "🔥 Fire"


class ChapterComment(models.Model):
    """Reader comment on a chapter."""

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chapter_comments",
    )
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Comment by {self.user.username} on ch.{self.chapter.number}"


class ChapterReaction(models.Model):
    """Reader reaction on a chapter (one per user per chapter)."""

    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chapter_reactions",
    )
    reaction_type = models.CharField(max_length=20, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("chapter", "user")]

    def __str__(self) -> str:
        return f"{self.user.username} → {self.reaction_type} on ch.{self.chapter.number}"
