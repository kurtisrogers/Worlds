"""Stripe payment service."""

from __future__ import annotations

import logging
from typing import Any

import stripe
from django.conf import settings
from django.urls import reverse

from payments.models import Transaction, TransactionStatus, TransactionType
from stories.models import Chapter, ReaderSubscription, Story, SubscriptionTier

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def calculate_fees(amount_cents: int) -> tuple[int, int]:
    """Return (platform_fee_cents, author_payout_cents) for a given amount."""
    fee = round(amount_cents * settings.PLATFORM_FEE_PERCENT / 100)
    return fee, amount_cents - fee


def create_chapter_checkout_session(
    user,
    chapter: Chapter,
    request,
) -> str | None:
    """Create a Stripe Checkout session for a one-time chapter unlock."""
    if not chapter.unlock_price_cents:
        return None

    amount = chapter.unlock_price_cents
    fee, payout = calculate_fees(amount)
    success_url = request.build_absolute_uri(
        reverse(
            "stories:chapter",
            kwargs={"slug": chapter.story.slug, "number": chapter.number},
        )
    )
    cancel_url = request.build_absolute_uri(chapter.get_absolute_url())

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=user.email,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount,
                    "product_data": {
                        "name": f"{chapter.story.title} — Chapter {chapter.number}",
                        "description": chapter.title,
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "type": "chapter_unlock",
            "chapter_id": str(chapter.id),
            "user_id": str(user.id),
            "platform_fee_cents": str(fee),
        },
        success_url=success_url + "?unlocked=1",
        cancel_url=cancel_url,
    )

    Transaction.objects.create(
        user=user,
        transaction_type=TransactionType.CHAPTER_UNLOCK,
        amount_cents=amount,
        platform_fee_cents=fee,
        author_payout_cents=payout,
        stripe_checkout_session_id=session.id,
        metadata={"chapter_id": chapter.id},
    )
    return session.url


def create_subscription_checkout_session(
    user,
    tier: SubscriptionTier,
    request,
) -> str | None:
    """Create a Stripe Checkout session for a subscription tier."""
    amount = tier.price_cents
    fee, payout = calculate_fees(amount)
    success_url = request.build_absolute_uri(tier.story.get_absolute_url())
    cancel_url = success_url

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount,
                    "recurring": {"interval": "month"},
                    "product_data": {
                        "name": f"{tier.story.title} — {tier.get_name_display()} Tier",
                        "description": tier.description
                        or f"Subscribe to {tier.story.title}",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "type": "subscription",
            "tier_id": str(tier.id),
            "story_id": str(tier.story_id),
            "user_id": str(user.id),
            "platform_fee_cents": str(fee),
        },
        success_url=success_url + "?subscribed=1",
        cancel_url=cancel_url,
    )

    Transaction.objects.create(
        user=user,
        transaction_type=TransactionType.SUBSCRIPTION,
        amount_cents=amount,
        platform_fee_cents=fee,
        author_payout_cents=payout,
        stripe_checkout_session_id=session.id,
        metadata={"tier_id": tier.id, "story_id": tier.story_id},
    )
    return session.url


def handle_checkout_completed(session: dict[str, Any]) -> None:
    """Process a completed Stripe checkout session."""
    metadata = session.get("metadata", {})
    session_type = metadata.get("type")
    user_id = metadata.get("user_id")

    Transaction.objects.filter(stripe_checkout_session_id=session["id"]).update(
        status=TransactionStatus.COMPLETED,
        stripe_payment_intent_id=session.get("payment_intent", ""),
    )

    if session_type == "chapter_unlock":
        from django.contrib.auth import get_user_model

        User = get_user_model()
        chapter_id = metadata.get("chapter_id")
        try:
            user = User.objects.get(pk=user_id)
            chapter = Chapter.objects.get(pk=chapter_id)
            from stories.models import ChapterUnlock

            ChapterUnlock.objects.get_or_create(
                reader=user,
                chapter=chapter,
                defaults={"amount_cents": chapter.unlock_price_cents or 0},
            )
        except (User.DoesNotExist, Chapter.DoesNotExist):
            logger.exception("Failed to process chapter unlock")

    elif session_type == "subscription":
        from django.contrib.auth import get_user_model

        User = get_user_model()
        tier_id = metadata.get("tier_id")
        try:
            user = User.objects.get(pk=user_id)
            tier = SubscriptionTier.objects.get(pk=tier_id)
            ReaderSubscription.objects.update_or_create(
                reader=user,
                story=tier.story,
                defaults={
                    "tier": tier,
                    "stripe_subscription_id": session.get("subscription", ""),
                    "status": ReaderSubscription.Status.ACTIVE,
                },
            )
        except (User.DoesNotExist, SubscriptionTier.DoesNotExist):
            logger.exception("Failed to process subscription")


def ensure_story_tiers(story: Story) -> None:
    """Create default subscription tiers for a story if missing."""
    from django.conf import settings as django_settings

    sort_order = 0
    for name, defaults in django_settings.TIER_DEFAULTS.items():
        SubscriptionTier.objects.get_or_create(
            story=story,
            name=name,
            defaults={
                "price_cents": defaults["price_cents"],
                "description": f"{defaults['label']} tier access to {story.title}",
                "benefits": [
                    f"Access to {defaults['label'].lower()}-tier chapters",
                    "Support the author directly",
                ],
                "sort_order": sort_order,
            },
        )
        sort_order += 1
