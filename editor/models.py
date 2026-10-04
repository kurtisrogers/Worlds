"""Records of AI calls. Prompt and response text are not stored."""

from django.conf import settings
from django.db import models


class AICall(models.Model):
    """Who invoked an AI call, when, and which story, chapter, and model."""

    class Outcome(models.TextChoices):
        SUCCESS = "success", "Success"
        PROVIDER_ERROR = "provider_error", "Provider error"
        TIMEOUT = "timeout", "Timeout"
        EMPTY = "empty", "Empty response"
        QUOTA = "quota", "Quota"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_calls",
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="ai_calls",
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        on_delete=models.CASCADE,
        related_name="ai_calls",
    )
    model = models.CharField(max_length=128)
    provider = models.CharField(max_length=32, default="openai")
    created_at = models.DateTimeField(auto_now_add=True)
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    sent_to_provider = models.BooleanField(default=False)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_cents = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.story_id} ch{self.chapter_id} {self.model}"


class ReviewFinding(models.Model):
    """A question or a gap note stored beside a chapter. Never chapter text."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISMISSED = "dismissed", "Dismissed"

    class Kind(models.TextChoices):
        QUESTION = "question", "Question"
        GAP = "gap", "Gap"

    chapter = models.ForeignKey(
        "stories.Chapter",
        on_delete=models.CASCADE,
        related_name="review_findings",
    )
    asked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_findings",
    )
    anchor = models.TextField(blank=True)
    question = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
    )
    model = models.CharField(max_length=128)
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.QUESTION,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["chapter", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.chapter_id} {self.kind} {self.status} {self.model}"
