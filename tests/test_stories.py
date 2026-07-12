"""Story model and access tests."""

import pytest
from django.urls import reverse

from stories.access import can_read_chapter, get_access_reason
from stories.models import Chapter, ReaderSubscription, SubscriptionTier, TierName
from tests.factories import ChapterFactory


@pytest.mark.django_db
class TestChapterAccess:
    def test_free_chapter_readable_by_anyone(self, published_chapter):
        assert can_read_chapter(None, published_chapter) is True

    def test_locked_chapter_requires_unlock(self, story, reader):
        chapter = ChapterFactory(
            story=story,
            number=2,
            unlock_price_cents=299,
            is_published=True,
        )
        assert can_read_chapter(reader, chapter) is False
        assert get_access_reason(reader, chapter) == "unlock"

    def test_tier_required_chapter(self, story, reader):
        chapter = ChapterFactory(
            story=story,
            number=3,
            tier_required=TierName.SILVER,
            is_published=True,
        )
        assert can_read_chapter(reader, chapter) is False
        assert get_access_reason(reader, chapter) == "subscribe"

    def test_subscriber_can_read_tier_chapter(self, story, reader):
        chapter = ChapterFactory(
            story=story,
            number=4,
            tier_required=TierName.BRONZE,
            is_published=True,
        )
        tier = SubscriptionTier.objects.get(story=story, name=TierName.BRONZE)
        ReaderSubscription.objects.create(
            reader=reader,
            story=story,
            tier=tier,
            status=ReaderSubscription.Status.ACTIVE,
        )
        assert can_read_chapter(reader, chapter) is True

    def test_author_can_read_own_draft(self, author, story):
        chapter = ChapterFactory(story=story, number=5, is_published=False)
        assert can_read_chapter(author, chapter) is True


@pytest.mark.django_db
class TestStoryViews:
    def test_home_page(self, client):
        response = client.get(reverse("stories:home"))
        assert response.status_code == 200
        assert b"Stories worth telling" in response.content

    def test_story_detail(self, client, story, published_chapter):
        response = client.get(reverse("stories:detail", kwargs={"slug": story.slug}))
        assert response.status_code == 200
        assert story.title.encode() in response.content

    def test_chapter_read(self, client, story, published_chapter):
        response = client.get(
            reverse(
                "stories:chapter",
                kwargs={"slug": story.slug, "number": published_chapter.number},
            )
        )
        assert response.status_code == 200
        assert published_chapter.content.encode() in response.content

    def test_dashboard_requires_login(self, client):
        response = client.get(reverse("stories:dashboard"))
        assert response.status_code == 302

    def test_author_dashboard(self, client_logged_in, story):
        response = client_logged_in.get(reverse("stories:dashboard"))
        assert response.status_code == 200
        assert story.title.encode() in response.content

    def test_create_story(self, client_logged_in):
        response = client_logged_in.post(
            reverse("stories:create"),
            {
                "title": "New Adventure",
                "synopsis": "A brand new tale.",
                "status": "draft",
                "content_source": "editor",
            },
        )
        assert response.status_code == 302
        from stories.models import Story

        assert Story.objects.filter(title="New Adventure").exists()
