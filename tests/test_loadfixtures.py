"""Tests for loadfixtures management command."""

import pytest
from django.core.management import call_command

from engagement.models import ChapterComment, ChapterReaction
from library.models import AuthorFollow, SavedStory
from stories.models import Chapter, ReaderSubscription, Story


@pytest.mark.django_db
class TestLoadFixtures:
    def test_loadfixtures_creates_data(self):
        call_command("loadfixtures", flush=True, no_covers=True)
        assert Story.objects.count() >= 8
        assert Chapter.objects.count() >= 20
        assert SavedStory.objects.count() >= 5
        assert AuthorFollow.objects.count() >= 5
        assert ReaderSubscription.objects.count() >= 3
        assert ChapterComment.objects.count() >= 5
        assert ChapterReaction.objects.count() >= 5

    def test_loadfixtures_creates_legacy_aliases(self):
        from django.contrib.auth.models import User

        call_command("loadfixtures", flush=True, no_covers=True)
        assert User.objects.filter(username="demo_author").exists()
        assert User.objects.filter(username="demo_reader").exists()

    def test_loadfixtures_creates_staff_users(self):
        from django.contrib.auth.models import User

        from accounts.models import PlatformRole, UserAccount

        call_command("loadfixtures", flush=True, no_covers=True)
        assert User.objects.filter(username="worlds_support").exists()
        support = UserAccount.objects.get(user__username="worlds_support")
        assert support.platform_role == PlatformRole.SUPPORT
        admin = User.objects.get(username="worlds_superadmin")
        assert admin.is_staff
        assert admin.is_superuser

    def test_loaddemo_alias(self):
        call_command("loaddemo", flush=True)
        assert Story.objects.filter(title="The Starlight Chronicle").exists()
