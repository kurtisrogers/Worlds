"""Tests for Stripe Connect."""

from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse

from accounts.models import AuthorProfile
from payments.connect import connect_payment_params, create_connect_account


@pytest.mark.django_db
class TestStripeConnect:
    def test_connect_payment_params_without_account(self, author):
        params = connect_payment_params(author, 1000)
        assert params == {}

    def test_connect_payment_params_with_account(self, author, settings):
        settings.PLATFORM_FEE_PERCENT = 2
        profile = author.author_profile
        profile.stripe_account_id = "acct_test123"
        profile.stripe_connect_onboarded = True
        profile.save()

        params = connect_payment_params(author, 1000)
        assert params["application_fee_amount"] == 20
        assert params["transfer_data"]["destination"] == "acct_test123"

    @patch("payments.connect.stripe.Account.create")
    def test_create_connect_account(self, mock_create, author):
        mock_create.return_value = MagicMock(id="acct_new123")
        account_id = create_connect_account(author)
        assert account_id == "acct_new123"
        profile = AuthorProfile.objects.get(user=author)
        assert profile.stripe_account_id == "acct_new123"

    def test_connect_dashboard_requires_login(self, client):
        response = client.get(reverse("payments:connect_dashboard"))
        assert response.status_code == 302
