"""Tests for engagement features."""

import pytest
from django.urls import reverse

from engagement.models import ChapterComment, ChapterReaction, ReactionType


@pytest.mark.django_db
class TestEngagement:
    def test_post_comment(self, client, reader, story, published_chapter):
        client.login(username="reader1", password="testpass123")
        url = reverse(
            "engagement:post_comment",
            kwargs={"slug": story.slug, "number": published_chapter.number},
        )
        response = client.post(url, {"body": "Loved this chapter!"})
        assert response.status_code == 200
        assert ChapterComment.objects.filter(chapter=published_chapter, user=reader).exists()

    def test_toggle_reaction(self, client, reader, story, published_chapter):
        client.login(username="reader1", password="testpass123")
        url = reverse(
            "engagement:toggle_reaction",
            kwargs={"slug": story.slug, "number": published_chapter.number},
        )
        response = client.post(url, {"reaction_type": ReactionType.LOVE})
        assert response.status_code == 200
        assert ChapterReaction.objects.filter(
            chapter=published_chapter, user=reader, reaction_type=ReactionType.LOVE
        ).exists()

    def test_chapter_shows_engagement(self, client, reader, story, published_chapter):
        ChapterComment.objects.create(
            chapter=published_chapter, user=reader, body="Great read!"
        )
        client.login(username="reader1", password="testpass123")
        response = client.get(
            reverse(
                "stories:chapter",
                kwargs={"slug": story.slug, "number": published_chapter.number},
            )
        )
        assert response.status_code == 200
        assert b"Great read!" in response.content
        assert b"React:" in response.content
