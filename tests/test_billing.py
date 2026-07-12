"""Billing area tests."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestBilling:
    def test_billing_requires_login(self, client):
        response = client.get(reverse("payments:billing"))
        assert response.status_code == 302
        assert "login" in response.url

    def test_billing_overview(self, client, reader):
        client.login(username=reader.username, password="testpass123")
        response = client.get(reverse("payments:billing"))
        assert response.status_code == 200
        assert b"Billing" in response.content

    def test_billing_tabs(self, client, reader):
        client.login(username=reader.username, password="testpass123")
        for tab in ("overview", "subscriptions", "purchases"):
            response = client.get(reverse("payments:billing"), {"tab": tab})
            assert response.status_code == 200

    def test_history_redirects_to_purchases(self, client, reader):
        client.login(username=reader.username, password="testpass123")
        response = client.get(reverse("payments:history"))
        assert response.status_code == 302
        assert response.url.endswith("?tab=purchases")

    def test_billing_summary_counts_subscription(self, client, reader, story):
        from payments.billing import get_billing_summary
        from payments.services import ensure_story_tiers
        from stories.models import ReaderSubscription, SubscriptionTier, TierName

        ensure_story_tiers(story)
        tier = SubscriptionTier.objects.get(story=story, name=TierName.BRONZE)
        ReaderSubscription.objects.create(
            reader=reader,
            story=story,
            tier=tier,
            status=ReaderSubscription.Status.ACTIVE,
        )
        summary = get_billing_summary(reader)
        assert summary["active_subscriptions"] == 1
