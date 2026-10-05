"""Jump anchors for review findings. Offsets are UTF-16 code units."""

import json
from pathlib import Path

import pytest
from django.urls import reverse

from editor.models import ReviewFinding
from editor.openai_provider import Completion
from stories.models import TierName
from tests.factories import ChapterFactory
from tests.test_chapter_review import (
    ANCHOR_ONE,
    QUESTION_ONE,
    StubProvider,
    _enable,
    _install,
    _json,
    _post,
    _snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "café 😀 "
QUOTE = ANCHOR_ONE
FINDING_KEYS = {
    "id",
    "question",
    "status",
    "start_offset",
    "quote",
    "anchor_status",
}


def _utf16_len(text):
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def _finding_completion(quote, question=QUESTION_ONE):
    return Completion(
        text=json.dumps({"findings": [{"quote": quote, "question": question}]}),
        model="gpt-review-model",
        input_tokens=4,
        output_tokens=4,
        usage_known=True,
    )


def _set_chapter(chapter, content):
    chapter.content = content
    chapter.save(update_fields=["content", "updated_at"])
    chapter.refresh_from_db()


def _list(client, story, number=1):
    return client.get(
        reverse("editor:findings", kwargs={"slug": story.slug, "number": number})
    )


@pytest.fixture
def chapter(story):
    created = ChapterFactory(
        story=story,
        number=1,
        title="Dawn",
        content=(
            "The river kept its course through the quiet valley, "
            "and the morning stayed with that one sentence."
        ),
        is_published=False,
        unlock_price_cents=424242,
        tier_required=TierName.GOLD,
    )
    ChapterFactory(
        story=story,
        number=2,
        title="Dusk",
        content="SIBLING_MANUSCRIPT_UNIQUE",
        is_published=False,
    )
    return created


def _autosave(client, story, content):
    return client.post(
        reverse("editor:autosave", kwargs={"slug": story.slug, "number": 1}),
        data=json.dumps({"title": "Dawn", "content": content}),
        content_type="application/json",
    )


@pytest.mark.django_db
class TestStoredAnchor:
    def test_utf16_offset_counts_accented_chars_and_emoji(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        content = PREFIX + QUOTE + " and then the valley."
        _set_chapter(chapter, content)
        before = _snapshot(chapter)
        _enable(settings)
        _install(monkeypatch, StubProvider(_finding_completion(QUOTE)))

        response = _post(client_logged_in, story)
        assert response.status_code == 200
        item = _json(response)["findings"][0]
        assert set(item) == FINDING_KEYS
        assert item["question"] == QUESTION_ONE
        assert item["status"] == "open"
        assert item["quote"] == QUOTE
        assert item["anchor_status"] == "ok"
        assert item["start_offset"] == _utf16_len(PREFIX)
        assert item["start_offset"] == 8
        assert len(PREFIX) == 7
        assert "é" in PREFIX
        assert "😀" in PREFIX
        assert "suggestion" not in item
        assert "replacement" not in item

        row = ReviewFinding.objects.get()
        assert row.quote == QUOTE
        assert row.start_offset == 8
        assert _snapshot(chapter) == before

    def test_quote_not_found_verbatim_stores_no_anchor(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        missing = "a sentence the writer never wrote"
        before = _snapshot(chapter)
        _enable(settings)
        _install(
            monkeypatch,
            StubProvider(_finding_completion(missing)),
        )
        response = _post(client_logged_in, story)
        item = _json(response)["findings"][0]
        assert item["question"] == QUESTION_ONE
        assert item["quote"] is None
        assert item["start_offset"] is None
        assert item["anchor_status"] == "none"
        row = ReviewFinding.objects.get()
        assert row.quote is None
        assert row.start_offset is None
        assert missing not in (row.anchor or "")
        assert missing not in (row.question or "")
        assert _snapshot(chapter) == before

    def test_quote_longer_than_120_keeps_a_verbatim_prefix(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        quote = ("The river kept its course through the quiet valley. " * 4).strip()
        assert len(quote) > 120
        _set_chapter(chapter, quote)
        before = _snapshot(chapter)
        _enable(settings)
        _install(monkeypatch, StubProvider(_finding_completion(quote)))
        response = _post(client_logged_in, story)
        item = _json(response)["findings"][0]
        assert item["quote"] == quote[:120]
        assert len(item["quote"]) == 120
        assert item["start_offset"] == 0
        assert item["anchor_status"] == "ok"
        assert chapter.content.startswith(item["quote"])
        assert _snapshot(chapter) == before


@pytest.mark.django_db
class TestAnchorStatus:
    def test_edited_away_quote_is_changed_and_does_not_write_the_finding(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(_finding_completion(QUOTE)))
        created = _post(client_logged_in, story)
        assert _json(created)["findings"][0]["anchor_status"] == "ok"
        row = ReviewFinding.objects.get()
        stored_offset = row.start_offset
        stored_quote = row.quote
        edited = "The valley is quiet now."
        saved = _autosave(client_logged_in, story, edited)
        assert saved.status_code == 200
        chapter.refresh_from_db()
        listed_at = chapter.updated_at

        listed = _list(client_logged_in, story)
        item = _json(listed)["findings"][0]
        assert item["anchor_status"] == "changed"
        assert item["start_offset"] is None
        assert item["quote"] == QUOTE
        row.refresh_from_db()
        assert row.start_offset == stored_offset
        assert row.quote == stored_quote
        assert row.question == QUESTION_ONE
        chapter.refresh_from_db()
        assert chapter.content == edited
        assert chapter.updated_at == listed_at

    def test_moved_unique_quote_is_ok_with_a_new_offset(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        original = "Intro " + QUOTE + " end."
        _set_chapter(chapter, original)
        _enable(settings)
        _install(monkeypatch, StubProvider(_finding_completion(QUOTE)))
        _post(client_logged_in, story)
        row = ReviewFinding.objects.get()
        stored_offset = row.start_offset
        assert stored_offset == _utf16_len("Intro ")
        moved_prefix = "Much later, "
        moved = moved_prefix + QUOTE + " only once."
        _autosave(client_logged_in, story, moved)
        chapter.refresh_from_db()
        seen = chapter.updated_at

        item = _json(_list(client_logged_in, story))["findings"][0]
        assert item["anchor_status"] == "ok"
        assert item["start_offset"] == _utf16_len(moved_prefix)
        assert item["start_offset"] != stored_offset
        assert item["quote"] == QUOTE
        row.refresh_from_db()
        assert row.start_offset == stored_offset
        assert row.quote == QUOTE
        chapter.refresh_from_db()
        assert chapter.content == moved
        assert chapter.updated_at == seen

    def test_duplicate_quote_is_changed_with_no_offset(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _set_chapter(chapter, "Intro " + QUOTE + " end.")
        _enable(settings)
        _install(monkeypatch, StubProvider(_finding_completion(QUOTE)))
        _post(client_logged_in, story)
        row = ReviewFinding.objects.get()
        stored_offset = row.start_offset
        duplicated = QUOTE + " and then " + QUOTE
        _autosave(client_logged_in, story, duplicated)
        chapter.refresh_from_db()
        seen = chapter.updated_at

        item = _json(_list(client_logged_in, story))["findings"][0]
        assert item["anchor_status"] == "changed"
        assert item["start_offset"] is None
        assert item["quote"] == QUOTE
        row.refresh_from_db()
        assert row.start_offset == stored_offset
        chapter.refresh_from_db()
        assert chapter.content == duplicated
        assert chapter.updated_at == seen

    def test_finding_without_an_anchor_reads_as_none(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)
        _install(
            monkeypatch,
            StubProvider(_finding_completion("nowhere in this chapter")),
        )
        _post(client_logged_in, story)
        before = _snapshot(chapter)
        item = _json(_list(client_logged_in, story))["findings"][0]
        assert item["anchor_status"] == "none"
        assert item["quote"] is None
        assert item["start_offset"] is None
        assert _snapshot(chapter) == before


class TestOffsetDocs:
    def test_readme_says_offsets_are_utf16_caret_indexes(self):
        readme = (ROOT / "README.md").read_text()
        assert "UTF-16" in readme
        assert "textarea" in readme
        assert "contenteditable" in readme
