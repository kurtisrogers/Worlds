"""Payment views including Stripe webhooks."""

import json
import logging

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from payments.models import Transaction
from payments.services import handle_checkout_completed

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(user=request.user)[:50]
    return render(
        request,
        "payments/history.html",
        {"transactions": transactions},
    )


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

    if event["type"] == "checkout.session.completed":
        handle_checkout_completed(event["data"]["object"])

    return HttpResponse(status=200)
