"""Platform role and staff area tests."""

import pytest
from django.urls import reverse

from accounts.models import PlatformRole, UserAccount
from accounts.roles import sync_django_staff_flags, user_has_role


@pytest.mark.django_db
class TestPlatformRoles:
    def test_new_user_gets_reader_account(self, client):
        client.post(
            reverse("accounts:register"),
            {
                "username": "roleuser",
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
        )
        from django.contrib.auth.models import User

        user = User.objects.get(username="roleuser")
        account = UserAccount.objects.get(user=user)
        assert account.platform_role == PlatformRole.READER

    def test_user_has_role_hierarchy(self, reader):
        account = UserAccount.objects.get(user=reader)
        account.platform_role = PlatformRole.MODERATOR
        account.save()
        sync_django_staff_flags(reader)

        assert user_has_role(reader, PlatformRole.SUPPORT)
        assert user_has_role(reader, PlatformRole.MODERATOR)
        assert not user_has_role(reader, PlatformRole.SUPER_ADMIN)

    def test_super_admin_syncs_django_flags(self, reader):
        account = UserAccount.objects.get(user=reader)
        account.platform_role = PlatformRole.SUPER_ADMIN
        account.save()
        sync_django_staff_flags(reader)
        reader.refresh_from_db()

        assert reader.is_staff
        assert reader.is_superuser

    def test_reader_cannot_access_staff(self, client, reader):
        client.login(username=reader.username, password="testpass123")
        response = client.get(reverse("staff:dashboard"))
        assert response.status_code == 302

    def test_support_can_access_staff_dashboard(self, client, reader):
        account = UserAccount.objects.get(user=reader)
        account.platform_role = PlatformRole.SUPPORT
        account.save()
        sync_django_staff_flags(reader)

        client.login(username=reader.username, password="testpass123")
        response = client.get(reverse("staff:dashboard"))
        assert response.status_code == 200
        assert b"Staff dashboard" in response.content

    def test_moderator_can_view_comments(self, client, reader):
        account = UserAccount.objects.get(user=reader)
        account.platform_role = PlatformRole.MODERATOR
        account.save()
        sync_django_staff_flags(reader)

        client.login(username=reader.username, password="testpass123")
        response = client.get(reverse("staff:comments"))
        assert response.status_code == 200

    def test_support_cannot_set_roles(self, client, reader, author):
        account = UserAccount.objects.get(user=reader)
        account.platform_role = PlatformRole.SUPPORT
        account.save()
        sync_django_staff_flags(reader)

        client.login(username=reader.username, password="testpass123")
        response = client.post(
            reverse("staff:set_role", kwargs={"username": author.username}),
            {"platform_role": PlatformRole.MODERATOR},
        )
        assert response.status_code == 302
        author_account = UserAccount.objects.get(user=author)
        assert author_account.platform_role == PlatformRole.READER

    def test_super_admin_can_set_roles(self, client, reader, author):
        admin_account = UserAccount.objects.get(user=reader)
        admin_account.platform_role = PlatformRole.SUPER_ADMIN
        admin_account.save()
        sync_django_staff_flags(reader)

        client.login(username=reader.username, password="testpass123")
        response = client.post(
            reverse("staff:set_role", kwargs={"username": author.username}),
            {"platform_role": PlatformRole.SUPPORT},
        )
        assert response.status_code == 302
        author_account = UserAccount.objects.get(user=author)
        assert author_account.platform_role == PlatformRole.SUPPORT
