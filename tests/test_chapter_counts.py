"""Counts for reads, likes, and favourites on released chapters."""

import json
from pathlib import Path

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from stories.engagement import (
    record_chapter_read,
    released_chapter_counts,
    set_chapter_favourite,
    set_chapter_like,
)
from stories.models import ChapterFavourite, ChapterLike, ChapterRead
from tests.factories import ChapterFactory, UserFactory

BASE_DIR = Path(__file__).resolve().parent.parent


def _counts_url(story):
    return reverse("stories:chapter_counts", kwargs={"slug": story.slug})


def _read_url(story, number):
    return reverse(
        "stories:record_read",
        kwargs={"slug": story.slug, "number": number},
    )


def _like_url(story, number):
    return reverse(
        "stories:chapter_like",
        kwargs={"slug": story.slug, "number": number},
    )


def _favourite_url(story, number):
    return reverse(
        "stories:chapter_favourite",
        kwargs={"slug": story.slug, "number": number},
    )


def _json(response):
    return json.loads(response.content.decode())


def _snapshot(chapter):
    chapter.refresh_from_db()
    story = chapter.story
    story.refresh_from_db()
    return {
        "title": chapter.title,
        "content": chapter.content,
        "is_published": chapter.is_published,
        "published_at": chapter.published_at,
        "updated_at": chapter.updated_at,
        "story_status": story.status,
        "story_updated_at": story.updated_at,
        "content_source": story.content_source,
    }


def _assert_counts_only(body, *secrets):
    assert set(body) == {"chapters"}
    raw = json.dumps(body)
    for secret in secrets:
        assert secret not in raw
    for row in body["chapters"]:
        assert set(row) == {"number", "reads", "likes", "favourites"}


@pytest.mark.django_db
class TestEngagementConstraints:
    def test_one_read_per_reader_per_chapter(self, reader, published_chapter):
        ChapterRead.objects.create(reader=reader, chapter=published_chapter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChapterRead.objects.create(reader=reader, chapter=published_chapter)

    def test_one_like_per_reader_per_chapter(self, reader, published_chapter):
        ChapterLike.objects.create(reader=reader, chapter=published_chapter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChapterLike.objects.create(reader=reader, chapter=published_chapter)

    def test_one_favourite_per_reader_per_chapter(self, reader, published_chapter):
        ChapterFavourite.objects.create(reader=reader, chapter=published_chapter)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ChapterFavourite.objects.create(
                    reader=reader, chapter=published_chapter
                )

    def test_two_readers_can_each_read_once(self, reader, published_chapter):
        other = UserFactory(username="second-reader")
        ChapterRead.objects.create(reader=reader, chapter=published_chapter)
        ChapterRead.objects.create(reader=other, chapter=published_chapter)
        assert ChapterRead.objects.filter(chapter=published_chapter).count() == 2


@pytest.mark.django_db
class TestReleasedChapterCounts:
    def test_author_sees_zeros_for_a_released_chapter_and_no_draft(
        self, client, author, story, published_chapter
    ):
        draft = ChapterFactory(
            story=story,
            number=2,
            title="Still drafting",
            content="DRAFT_TEXT_SECRET",
            is_published=False,
        )
        client.force_login(author)
        response = client.get(_counts_url(story))
        assert response.status_code == 200
        assert response["Cache-Control"] == "no-store"
        body = _json(response)
        _assert_counts_only(body, author.username, draft.content)
        assert body == {
            "chapters": [
                {"number": 1, "reads": 0, "likes": 0, "favourites": 0},
            ]
        }

    def test_draft_with_a_stored_row_is_still_absent(
        self, client, author, reader, story, published_chapter
    ):
        draft = ChapterFactory(story=story, number=2, is_published=False)
        ChapterRead.objects.create(reader=reader, chapter=draft)
        ChapterLike.objects.create(reader=reader, chapter=draft)
        ChapterFavourite.objects.create(reader=reader, chapter=draft)
        client.force_login(author)
        body = _json(client.get(_counts_url(story)))
        assert [row["number"] for row in body["chapters"]] == [published_chapter.number]
        assert released_chapter_counts(story)[0]["reads"] == 0

    def test_unpublished_chapter_drops_out_of_the_response(
        self, client, author, reader, story, published_chapter
    ):
        record_chapter_read(reader, published_chapter)
        published_chapter.is_published = False
        published_chapter.save(update_fields=["is_published", "updated_at"])
        client.force_login(author)
        body = _json(client.get(_counts_url(story)))
        assert body == {"chapters": []}

    def test_counts_are_not_multiplied_across_relations(
        self, client, author, story, published_chapter
    ):
        first = UserFactory(username="reader-one-unique")
        second = UserFactory(username="reader-two-unique")
        third = UserFactory(username="reader-three-unique")
        for person in (first, second):
            record_chapter_read(person, published_chapter)
            set_chapter_like(person, published_chapter, liked=True)
        set_chapter_favourite(third, published_chapter, favourited=True)
        client.force_login(author)
        response = client.get(_counts_url(story))
        body = _json(response)
        _assert_counts_only(
            body,
            first.username,
            second.username,
            third.username,
            first.email,
            published_chapter.content,
        )
        assert body["chapters"] == [
            {"number": 1, "reads": 2, "likes": 2, "favourites": 1}
        ]

    def test_another_user_cannot_read_counts(
        self, client, reader, story, published_chapter
    ):
        client.force_login(reader)
        response = client.get(_counts_url(story))
        assert response.status_code == 404
        assert published_chapter.content.encode() not in response.content

    def test_another_author_cannot_read_counts(self, client, story, published_chapter):
        other = UserFactory(username="other-author")
        client.force_login(other)
        assert client.get(_counts_url(story)).status_code == 404

    def test_anonymous_counts_require_sign_in(self, client, story, published_chapter):
        response = client.get(_counts_url(story))
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_missing_story_is_not_found(self, client, author):
        client.force_login(author)
        response = client.get(
            reverse("stories:chapter_counts", kwargs={"slug": "missing"})
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestRecording:
    def test_read_like_and_favourite_are_idempotent(
        self, client, reader, story, published_chapter
    ):
        client.force_login(reader)
        assert client.post(_read_url(story, 1)).status_code == 200
        again = client.post(_read_url(story, 1))
        assert again.status_code == 200
        assert _json(again) == {"recorded": True}
        assert ChapterRead.objects.filter(chapter=published_chapter).count() == 1

        assert _json(client.post(_like_url(story, 1))) == {"liked": True}
        assert _json(client.post(_like_url(story, 1))) == {"liked": True}
        assert ChapterLike.objects.filter(chapter=published_chapter).count() == 1
        assert _json(client.delete(_like_url(story, 1))) == {"liked": False}
        assert _json(client.delete(_like_url(story, 1))) == {"liked": False}
        assert ChapterLike.objects.filter(chapter=published_chapter).count() == 0

        assert _json(client.post(_favourite_url(story, 1))) == {"favourited": True}
        assert _json(client.post(_favourite_url(story, 1))) == {"favourited": True}
        assert ChapterFavourite.objects.filter(chapter=published_chapter).count() == 1
        assert _json(client.delete(_favourite_url(story, 1))) == {"favourited": False}
        assert _json(client.delete(_favourite_url(story, 1))) == {"favourited": False}
        assert ChapterFavourite.objects.count() == 0

    def test_draft_read_like_and_favourite_are_absent(
        self, client, reader, author, story
    ):
        draft = ChapterFactory(
            story=story,
            number=4,
            content="UNPUBLISHED_BODY",
            is_published=False,
        )
        client.force_login(reader)
        assert client.post(_read_url(story, draft.number)).status_code == 404
        assert client.post(_like_url(story, draft.number)).status_code == 404
        assert client.post(_favourite_url(story, draft.number)).status_code == 404
        assert record_chapter_read(reader, draft) is False
        assert set_chapter_like(reader, draft, liked=True) is False
        assert set_chapter_favourite(reader, draft, favourited=True) is False
        assert ChapterRead.objects.count() == 0
        assert ChapterLike.objects.count() == 0
        assert ChapterFavourite.objects.count() == 0

        client.force_login(author)
        assert _json(client.get(_counts_url(story))) == {"chapters": []}

    def test_opening_a_draft_or_the_editor_does_not_record_a_read(
        self, client, author, reader, story, published_chapter
    ):
        draft = ChapterFactory(story=story, number=5, is_published=False)
        client.force_login(author)
        editor = client.get(
            reverse(
                "editor:edit",
                kwargs={"slug": story.slug, "number": draft.number},
            )
        )
        assert editor.status_code == 200
        html = editor.content.decode()
        assert _counts_url(story) not in html
        assert "/reads/" not in html
        assert "/likes/" not in html
        assert "/favourites/" not in html
        assert 'id="manuscript"' in html
        draft_page = client.get(
            reverse(
                "stories:chapter",
                kwargs={"slug": story.slug, "number": draft.number},
            )
        )
        assert draft_page.status_code == 200

        client.force_login(reader)
        released_page = client.get(
            reverse(
                "stories:chapter",
                kwargs={"slug": story.slug, "number": published_chapter.number},
            )
        )
        assert released_page.status_code == 200
        assert ChapterRead.objects.count() == 0
        assert ChapterLike.objects.count() == 0
        assert ChapterFavourite.objects.count() == 0

    def test_editor_assets_do_not_call_the_counts_endpoint(self):
        template = (BASE_DIR / "templates" / "editor" / "edit.html").read_text()
        script = (BASE_DIR / "static" / "editor" / "autosave.js").read_text()
        for source in (template, script):
            assert "/counts/" not in source
            assert "/reads/" not in source
            assert "/likes/" not in source
            assert "/favourites/" not in source

    def test_anonymous_recording_is_refused(self, client, story, published_chapter):
        read = client.post(_read_url(story, 1))
        like = client.post(_like_url(story, 1))
        favourite = client.post(_favourite_url(story, 1))
        assert read.status_code == 302
        assert like.status_code == 302
        assert favourite.status_code == 302
        assert ChapterRead.objects.count() == 0
        assert ChapterLike.objects.count() == 0
        assert ChapterFavourite.objects.count() == 0

    def test_recording_does_not_change_chapter_text_or_publish_state(
        self, client, author, reader, story, published_chapter
    ):
        draft = ChapterFactory(
            story=story,
            number=6,
            title="Draft title",
            content="Draft body stays put.",
            is_published=False,
        )
        before_released = _snapshot(published_chapter)
        before_draft = _snapshot(draft)
        before_story_status = story.status

        client.force_login(reader)
        client.post(_read_url(story, published_chapter.number))
        client.post(_read_url(story, published_chapter.number))
        client.post(_like_url(story, published_chapter.number))
        client.delete(_like_url(story, published_chapter.number))
        client.post(_like_url(story, published_chapter.number))
        client.post(_favourite_url(story, published_chapter.number))
        client.delete(_favourite_url(story, published_chapter.number))
        client.post(_favourite_url(story, published_chapter.number))
        client.post(_read_url(story, draft.number))
        client.post(_like_url(story, draft.number))
        client.post(_favourite_url(story, draft.number))

        client.force_login(author)
        client.get(
            reverse(
                "editor:edit",
                kwargs={"slug": story.slug, "number": published_chapter.number},
            )
        )
        client.get(_counts_url(story))

        assert _snapshot(published_chapter) == before_released
        assert _snapshot(draft) == before_draft
        story.refresh_from_db()
        assert story.status == before_story_status
        assert ChapterRead.objects.filter(chapter=published_chapter).count() == 1
        assert ChapterLike.objects.filter(chapter=published_chapter).count() == 1
        assert ChapterFavourite.objects.filter(chapter=published_chapter).count() == 1
        assert not ChapterRead.objects.filter(chapter=draft).exists()
