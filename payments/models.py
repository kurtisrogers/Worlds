"""Payment transaction records."""

from django.conf import settings
from django.db import models


class TransactionType(models.TextChoices):
    SUBSCRIPTION = "subscription", "Subscription"
    CHAPTER_UNLOCK = "chapter_unlock", "Chapter Unlock"


class TransactionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


class Transaction(models.Model):
    """Record of a payment transaction with platform fee."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount_cents = models.PositiveIntegerField()
    platform_fee_cents = models.PositiveIntegerField()
    author_payout_cents = models.PositiveIntegerField()
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.transaction_type} — ${self.amount_cents / 100:.2f}"
