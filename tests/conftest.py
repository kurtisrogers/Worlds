"""Pytest configuration."""

import pytest


@pytest.fixture
def author(db):
    from tests.factories import UserFactory

    return UserFactory(username="author1")


@pytest.fixture
def reader(db):
    from tests.factories import UserFactory

    return UserFactory(username="reader1")


@pytest.fixture
def story(author):
    from payments.services import ensure_story_tiers
    from tests.factories import StoryFactory

    s = StoryFactory(author=author, title="The Lost Kingdom")
    ensure_story_tiers(s)
    return s


@pytest.fixture
def published_chapter(story):
    from tests.factories import ChapterFactory

    return ChapterFactory(
        story=story,
        number=1,
        title="The Beginning",
        content="The kingdom lay silent under a silver moon.",
        is_published=True,
    )


@pytest.fixture
def client_logged_in(client, author):
    client.login(username="author1", password="testpass123")
    return client
