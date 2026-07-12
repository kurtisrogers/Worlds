"""Payment service tests."""

import pytest

from payments.services import calculate_fees, ensure_story_tiers
from stories.models import SubscriptionTier, TierName


@pytest.mark.django_db
class TestPaymentFees:
    def test_calculate_fees_two_percent(self, settings):
        settings.PLATFORM_FEE_PERCENT = 2
        fee, payout = calculate_fees(1000)
        assert fee == 20
        assert payout == 980

    def test_ensure_story_tiers_creates_defaults(self, story):
        SubscriptionTier.objects.filter(story=story).delete()
        ensure_story_tiers(story)
        tiers = SubscriptionTier.objects.filter(story=story)
        assert tiers.count() == 3
        assert set(tiers.values_list("name", flat=True)) == {
            TierName.BRONZE,
            TierName.SILVER,
            TierName.GOLD,
        }
