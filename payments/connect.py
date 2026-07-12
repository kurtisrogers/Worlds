"""Stripe Connect services for author payouts."""

from __future__ import annotations

import logging

import stripe
from django.conf import settings
from django.urls import reverse

from accounts.models import AuthorProfile

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def get_author_stripe_account(author) -> str | None:
    """Return the author's Stripe Connect account ID if onboarded."""
    try:
        profile = author.author_profile
    except AuthorProfile.DoesNotExist:
        return None
    if profile.stripe_account_id and profile.stripe_connect_onboarded:
        return profile.stripe_account_id
    return None


def create_connect_account(user) -> str:
    """Create a Stripe Express account for an author."""
    profile, _ = AuthorProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": user.username},
    )
    if profile.stripe_account_id:
        return profile.stripe_account_id

    account = stripe.Account.create(
        type="express",
        country="US",
        email=user.email or None,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
        metadata={"user_id": str(user.id), "username": user.username},
    )
    profile.stripe_account_id = account.id
    profile.save(update_fields=["stripe_account_id", "updated_at"])
    return account.id


def create_account_link(user, request) -> str:
    """Generate a Stripe Account Link for onboarding or refresh."""
    account_id = create_connect_account(user)
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=request.build_absolute_uri(reverse("payments:connect_refresh")),
        return_url=request.build_absolute_uri(reverse("payments:connect_return")),
        type="account_onboarding",
    )
    return link.url


def refresh_connect_status(user) -> bool:
    """Check Stripe account status and update onboarded flag."""
    try:
        profile = user.author_profile
    except AuthorProfile.DoesNotExist:
        return False
    if not profile.stripe_account_id:
        return False

    account = stripe.Account.retrieve(profile.stripe_account_id)
    charges_enabled = account.get("charges_enabled", False)
    payouts_enabled = account.get("payouts_enabled", False)
    onboarded = charges_enabled and payouts_enabled
    if onboarded != profile.stripe_connect_onboarded:
        profile.stripe_connect_onboarded = onboarded
        profile.save(update_fields=["stripe_connect_onboarded", "updated_at"])
    return onboarded


def connect_payment_params(author, amount_cents: int) -> dict:
    """Build Stripe Connect params for destination charges."""
    account_id = get_author_stripe_account(author)
    if not account_id:
        return {}

    fee = round(amount_cents * settings.PLATFORM_FEE_PERCENT / 100)
    return {
        "application_fee_amount": fee,
        "transfer_data": {"destination": account_id},
    }


def connect_subscription_params(author) -> dict:
    """Build Stripe Connect params for subscription checkout."""
    account_id = get_author_stripe_account(author)
    if not account_id:
        return {}

    return {
        "application_fee_percent": float(settings.PLATFORM_FEE_PERCENT),
        "transfer_data": {"destination": account_id},
    }
