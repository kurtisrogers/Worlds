"""Editor autosave tests."""

import json

import pytest
from django.urls import reverse

from tests.factories import ChapterFactory


@pytest.mark.django_db
class TestEditor:
    def test_autosave_updates_chapter(self, client_logged_in, story):
        chapter = ChapterFactory(
            story=story, number=1, title="Old", content="Old content"
        )
        url = reverse("editor:autosave", kwargs={"slug": story.slug, "number": 1})
        response = client_logged_in.post(
            url,
            data=json.dumps(
                {
                    "title": "New Title",
                    "content": "<p>New <strong>content</strong> here.</p>",
                    "content_format": "html",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        chapter.refresh_from_db()
        assert chapter.title == "New Title"
        assert "<strong>" in chapter.content
        assert chapter.content_format == "html"

    def test_editor_requires_author(self, client, story, reader):
        ChapterFactory(story=story, number=1)
        client.login(username="reader1", password="testpass123")
        url = reverse("editor:edit", kwargs={"slug": story.slug, "number": 1})
        response = client.get(url)
        assert response.status_code == 404
