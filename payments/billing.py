"""Billing helpers and Stripe Customer Portal."""

from __future__ import annotations

import logging

import stripe
from django.conf import settings
from django.db.models import Sum
from django.urls import reverse

from accounts.roles import get_user_account
from payments.models import Transaction, TransactionStatus
from stories.models import ChapterUnlock, ReaderSubscription

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def get_billing_summary(user) -> dict:
    """Aggregate billing stats for a user's dashboard."""
    active_subs = ReaderSubscription.objects.filter(
        reader=user,
        status=ReaderSubscription.Status.ACTIVE,
    ).count()
    total_spent = (
        Transaction.objects.filter(
            user=user,
            status=TransactionStatus.COMPLETED,
        ).aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    unlock_count = ChapterUnlock.objects.filter(reader=user).count()
    account = get_user_account(user)
    return {
        "active_subscriptions": active_subs,
        "total_spent_cents": total_spent,
        "chapter_unlocks": unlock_count,
        "has_stripe_customer": bool(account and account.stripe_customer_id),
    }


def ensure_stripe_customer(user) -> str | None:
    """Get or create a Stripe Customer for billing portal access."""
    account = get_user_account(user)
    if not account:
        return None
    if account.stripe_customer_id:
        return account.stripe_customer_id

    try:
        customer = stripe.Customer.create(
            email=user.email or None,
            metadata={"user_id": str(user.id), "username": user.username},
        )
        account.stripe_customer_id = customer.id
        account.save(update_fields=["stripe_customer_id", "updated_at"])
        return customer.id
    except Exception:
        logger.exception("Failed to create Stripe customer for user %s", user.pk)
        return None


def create_billing_portal_session(user, request) -> str | None:
    """Create a Stripe Billing Portal session URL."""
    customer_id = ensure_stripe_customer(user)
    if not customer_id:
        return None
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=request.build_absolute_uri(reverse("payments:billing")),
        )
        return session.url
    except Exception:
        logger.exception("Failed to create billing portal for user %s", user.pk)
        return None


def save_customer_from_checkout(user, customer_id: str | None) -> None:
    """Persist Stripe customer ID from a checkout session."""
    if not customer_id:
        return
    account = get_user_account(user)
    if account and not account.stripe_customer_id:
        account.stripe_customer_id = customer_id
        account.save(update_fields=["stripe_customer_id", "updated_at"])
