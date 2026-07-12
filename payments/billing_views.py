"""Billing area views for readers and authors."""

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from payments.billing import create_billing_portal_session, get_billing_summary
from payments.models import Transaction, TransactionStatus
from stories.models import ChapterUnlock, ReaderSubscription


@login_required
def billing_overview(request):
    tab = request.GET.get("tab", "overview")
    valid_tabs = ("overview", "subscriptions", "purchases", "earnings")
    if tab not in valid_tabs:
        tab = "overview"

    summary = get_billing_summary(request.user)
    subscriptions = ReaderSubscription.objects.filter(
        reader=request.user
    ).select_related("story", "tier")
    unlocks = ChapterUnlock.objects.filter(reader=request.user).select_related(
        "chapter", "chapter__story"
    )[:50]
    transactions = Transaction.objects.filter(user=request.user)[:50]

    author_profile = getattr(request.user, "author_profile", None)
    author_unlock_revenue = 0
    has_author_stories = request.user.stories.exists()
    if has_author_stories:
        author_unlock_revenue = (
            ChapterUnlock.objects.filter(
                chapter__story__author=request.user
            ).aggregate(total=Sum("amount_cents"))["total"]
            or 0
        )

    if request.GET.get("portal") == "1":
        portal_url = create_billing_portal_session(request.user, request)
        if portal_url:
            return redirect(portal_url)

    return render(
        request,
        "payments/billing.html",
        {
            "tab": tab,
            "summary": summary,
            "subscriptions": subscriptions,
            "unlocks": unlocks,
            "transactions": transactions,
            "author_profile": author_profile,
            "author_unlock_revenue_cents": author_unlock_revenue,
            "has_author_stories": has_author_stories,
        },
    )


@login_required
def billing_portal(request):
    """Redirect to Stripe Customer Portal for payment method management."""
    url = create_billing_portal_session(request.user, request)
    if url:
        return redirect(url)
    return redirect("payments:billing")


@login_required
def transaction_history(request):
    """Legacy URL — redirect to billing purchases tab."""
    from django.urls import reverse

    return redirect(f"{reverse('payments:billing')}?tab=purchases")
