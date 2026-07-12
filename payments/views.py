"""Payment views including Stripe webhooks and Connect onboarding."""

import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import AuthorProfile
from payments.connect import (
    create_account_link,
    refresh_connect_status,
)
from payments.models import Transaction
from payments.services import handle_checkout_completed

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def connect_dashboard(request):
    profile, _ = AuthorProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.username},
    )
    if profile.stripe_account_id:
        refresh_connect_status(request.user)

    return render(
        request,
        "payments/connect.html",
        {
            "profile": profile,
            "onboarded": profile.stripe_connect_onboarded,
        },
    )


@login_required
def connect_onboard(request):
    url = create_account_link(request.user, request)
    return redirect(url)


@login_required
def connect_return(request):
    onboarded = refresh_connect_status(request.user)
    if onboarded:
        messages.success(request, "Stripe Connect setup complete! You can now receive payouts.")
    else:
        messages.info(request, "Stripe setup in progress. Complete any remaining steps.")
    return redirect("payments:connect_dashboard")


@login_required
def connect_refresh(request):
    url = create_account_link(request.user, request)
    return redirect(url)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponseBadRequest("Invalid signature")

    event_type = event["type"]
    data_object = event["data"]["object"]

    if event_type == "checkout.session.completed":
        handle_checkout_completed(data_object)
    elif event_type == "account.updated":
        _handle_account_updated(data_object)

    return HttpResponse(status=200)


def _handle_account_updated(account: dict) -> None:
    user_id = account.get("metadata", {}).get("user_id")
    if not user_id:
        return
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        refresh_connect_status(user)
    except User.DoesNotExist:
        logger.warning("account.updated for unknown user_id %s", user_id)
