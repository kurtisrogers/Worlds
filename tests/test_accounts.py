"""Account tests."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestAccounts:
    def test_register_creates_user_and_profile(self, client):
        response = client.post(
            reverse("accounts:register"),
            {
                "username": "newauthor",
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
        )
        assert response.status_code == 302
        from accounts.models import AuthorProfile
        from django.contrib.auth.models import User

        user = User.objects.get(username="newauthor")
        assert AuthorProfile.objects.filter(user=user).exists()

    def test_login_page(self, client):
        response = client.get(reverse("accounts:login"))
        assert response.status_code == 200
