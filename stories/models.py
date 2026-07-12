"""Story, chapter, and subscription models."""

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class StoryStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHING = "publishing", "Publishing"
    PUBLISHED = "published", "Published"


class ContentSource(models.TextChoices):
    EDITOR = "editor", "In-app Editor"
    UPLOAD = "upload", "Document Upload"
    SHEETS = "sheets", "Google Sheets"


class TierName(models.TextChoices):
    NONE = "none", "Free"
    BRONZE = "bronze", "Bronze"
    SILVER = "silver", "Silver"
    GOLD = "gold", "Gold"


class Story(models.Model):
    """A book or serial story being written by an author."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stories",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    synopsis = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=StoryStatus.choices,
        default=StoryStatus.DRAFT,
    )
    content_source = models.CharField(
        max_length=20,
        choices=ContentSource.choices,
        default=ContentSource.EDITOR,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name_plural = "stories"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "story"
            slug = base
            counter = 1
            while Story.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("stories:detail", kwargs={"slug": self.slug})

    @property
    def chapter_count(self) -> int:
        return self.chapters.count()


class Chapter(models.Model):
    """A single chapter within a story."""

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    unlock_price_cents = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="One-time unlock price in cents. Leave blank for tier-only access.",
    )
    tier_required = models.CharField(
        max_length=20,
        choices=TierName.choices,
        default=TierName.NONE,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["number"]
        unique_together = [("story", "number")]

    def __str__(self) -> str:
        return f"{self.story.title} — Ch. {self.number}: {self.title}"

    def get_absolute_url(self) -> str:
        return reverse(
            "stories:chapter",
            kwargs={"slug": self.story.slug, "number": self.number},
        )

    @property
    def is_free(self) -> bool:
        return (
            self.tier_required == TierName.NONE
            and not self.unlock_price_cents
        )


class SubscriptionTier(models.Model):
    """Per-story subscription tier (bronze, silver, gold)."""

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="subscription_tiers",
    )
    name = models.CharField(max_length=20, choices=TierName.choices)
    price_cents = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    benefits = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price_cents"]
        unique_together = [("story", "name")]

    def __str__(self) -> str:
        return f"{self.story.title} — {self.get_name_display()}"

    @property
    def price_dollars(self) -> str:
        return f"${self.price_cents / 100:.2f}"


class ReaderSubscription(models.Model):
    """Active reader subscription to a story tier."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        PAST_DUE = "past_due", "Past Due"

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="reader_subscriptions",
    )
    tier = models.ForeignKey(
        SubscriptionTier,
        on_delete=models.PROTECT,
        related_name="subscribers",
    )
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("reader", "story")]

    def __str__(self) -> str:
        return f"{self.reader.username} → {self.story.title} ({self.tier.name})"


class ChapterUnlock(models.Model):
    """One-time chapter purchase by a reader."""

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chapter_unlocks",
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="unlocks",
    )
    amount_cents = models.PositiveIntegerField()
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("reader", "chapter")]

    def __str__(self) -> str:
        return f"{self.reader.username} unlocked {self.chapter}"
