"""Tests for Google OAuth integration."""

import pytest
from django.urls import reverse

from integrations.google_oauth import user_has_google_credentials
from integrations.models import GoogleCredential


@pytest.mark.django_db
class TestGoogleOAuth:
    def test_user_has_credentials_false(self, author):
        assert user_has_google_credentials(author) is False

    def test_user_has_credentials_true(self, author):
        GoogleCredential.objects.create(
            user=author,
            access_token="test_token",
            refresh_token="test_refresh",
        )
        assert user_has_google_credentials(author) is True

    def test_google_auth_start_requires_login(self, client):
        response = client.get(reverse("integrations:google_auth_start"))
        assert response.status_code == 302

    def test_google_auth_start_redirects(self, client, author, settings):
        settings.GOOGLE_CLIENT_ID = "test-client-id"
        settings.GOOGLE_CLIENT_SECRET = "test-secret"
        client.login(username="author1", password="testpass123")
        response = client.get(reverse("integrations:google_auth_start"))
        assert response.status_code == 302
        assert "accounts.google.com" in response.url
