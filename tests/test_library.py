"""Library feature tests."""

import pytest
from django.urls import reverse

from library.models import AuthorFollow, SavedStory
from tests.factories import UserFactory


@pytest.mark.django_db
class TestLibrary:
    def test_library_requires_login(self, client):
        response = client.get(reverse("library:index"))
        assert response.status_code == 302

    def test_save_story_to_collection(self, client, reader, story):
        client.login(username="reader1", password="testpass123")
        url = reverse("library:toggle_save", kwargs={"slug": story.slug})
        response = client.post(url)
        assert response.status_code == 302
        assert SavedStory.objects.filter(user=reader, story=story).exists()

    def test_unsave_story(self, client, reader, story):
        SavedStory.objects.create(user=reader, story=story)
        client.login(username="reader1", password="testpass123")
        url = reverse("library:toggle_save", kwargs={"slug": story.slug})
        client.post(url)
        assert not SavedStory.objects.filter(user=reader, story=story).exists()

    def test_follow_author(self, client, reader, author):
        client.login(username="reader1", password="testpass123")
        url = reverse("library:toggle_follow", kwargs={"username": "author1"})
        response = client.post(url)
        assert response.status_code == 302
        assert AuthorFollow.objects.filter(follower=reader, author=author).exists()

    def test_library_saved_tab(self, client, reader, story):
        SavedStory.objects.create(user=reader, story=story)
        client.login(username="reader1", password="testpass123")
        response = client.get(reverse("library:index"), {"tab": "saved"})
        assert response.status_code == 200
        assert story.title.encode() in response.content

    def test_author_profile_page(self, client, author, story):
        response = client.get(reverse("library:author", kwargs={"username": "author1"}))
        assert response.status_code == 200
        assert story.title.encode() in response.content

    def test_story_detail_shows_save_button(self, client, reader, story, published_chapter):
        client.login(username="reader1", password="testpass123")
        response = client.get(reverse("stories:detail", kwargs={"slug": story.slug}))
        assert response.status_code == 200
        assert b"Add to library" in response.content
