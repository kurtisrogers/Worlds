"""Chapter review records. The model is stubbed. These tests must not call OpenAI."""

import json
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from freezegun import freeze_time

from editor.models import AICall, ReviewFinding
from editor.openai_provider import (
    Completion,
    OpenAIError,
    OpenAIProvider,
    OpenAIQuota,
    OpenAITimeout,
)
from editor.policy import review_instructions, review_prompt, system_instructions
from stories.models import ChapterUnlock, ReaderSubscription, TierName
from tests.factories import ChapterFactory, StoryFactory, UserFactory

ROOT = Path(__file__).resolve().parents[1]
PARAGRAPH = (
    "The river kept its course through the quiet valley, "
    "and the morning stayed with that one sentence."
)
REWRITE = (
    "A model wrote this chapter instead, sending the river out of the valley "
    "and into a city the writer never drafted."
)
QUESTION_ONE = "Does the river stay in the valley?"
QUESTION_TWO = "What does the morning hold after this?"
ANCHOR_ONE = "The river kept its course"
ANCHOR_TWO = "the morning stayed"
GAP = "Nothing proved. The chapter text is unchanged."
REWRITE_NOTE = "The model returned replacement prose. Nothing was applied."
AUTHORSHIP = "This is assistance, not authorship."
PROMPT_REJECTION = "The client cannot set the system prompt."
SPEND_REJECTION = "A configured spend cap rejected this call."
SECRET = "sk-test-not-a-real-key"
SIBLING = "SIBLING_MANUSCRIPT_UNIQUE"
OTHER_MANUSCRIPT = "OTHER_AUTHOR_MANUSCRIPT_UNIQUE"
PAYMENT = "pi_UNIQUE_READER_PAYMENT"
SUBSCRIPTION = "sub_UNIQUE_READER_PAYMENT"
BANNED_ALL_CLEAR = ("no gaps", "all clear", "all-clear", "no issues", "looks good")


class StubProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _review_url(story, number=1):
    return reverse("editor:review", kwargs={"slug": story.slug, "number": number})


def _dismiss_url(story, finding_id, number=1):
    return reverse(
        "editor:dismiss",
        kwargs={"slug": story.slug, "number": number, "finding_id": finding_id},
    )


def _edit_url(story, number=1):
    return reverse("editor:edit", kwargs={"slug": story.slug, "number": number})


def _autosave_url(story, number=1):
    return reverse("editor:autosave", kwargs={"slug": story.slug, "number": number})


def _completion(**overrides):
    data = {
        "text": _questions_payload(),
        "model": "gpt-review-model",
        "input_tokens": 11,
        "output_tokens": 7,
        "usage_known": True,
    }
    data.update(overrides)
    return Completion(**data)


def _questions_payload():
    return json.dumps(
        {
            "findings": [
                {"quote": ANCHOR_ONE, "question": QUESTION_ONE},
                {"quote": ANCHOR_TWO, "question": QUESTION_TWO},
            ]
        }
    )


def _enable(settings, **extra):
    settings.AI_ASSIST_ENABLED = True
    settings.WORLDS_ENVIRONMENT = "local"
    settings.OPENAI_API_KEY = SECRET
    settings.OPENAI_MODEL = "gpt-test-model"
    settings.OPENAI_TIMEOUT_SECONDS = 30
    settings.AI_USER_RATE_LIMIT = None
    settings.AI_USER_RATE_WINDOW_SECONDS = None
    settings.AI_SPEND_CAP_CENTS = None
    settings.AI_SPEND_WINDOW_SECONDS = None
    settings.OPENAI_INPUT_CENTS_PER_MILLION_TOKENS = None
    settings.OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS = None
    for key, value in extra.items():
        setattr(settings, key, value)


def _install(monkeypatch, stub):
    monkeypatch.setattr("editor.assist.get_provider", lambda: stub)
    return stub


def _post(client, story, payload=None, number=1):
    if payload is None:
        body = b""
        content_type = "application/json"
    elif isinstance(payload, dict | list):
        body = json.dumps(payload)
        content_type = "application/json"
    else:
        body = payload
        content_type = "application/json"
    return client.post(
        _review_url(story, number),
        data=body,
        content_type=content_type,
    )


def _json(response):
    return json.loads(response.content.decode())


def _snapshot(chapter):
    chapter.refresh_from_db()
    return {
        "title": chapter.title,
        "content": chapter.content,
        "updated_at": chapter.updated_at,
        "is_published": chapter.is_published,
        "unlock_price_cents": chapter.unlock_price_cents,
        "tier_required": chapter.tier_required,
    }


def _stored_text():
    chunks = []
    for finding in ReviewFinding.objects.all():
        for field in finding._meta.fields:
            value = getattr(finding, field.attname if field.is_relation else field.name)
            if isinstance(value, str):
                chunks.append(value)
    for call in AICall.objects.all():
        for field in call._meta.fields:
            value = getattr(call, field.name)
            if isinstance(value, str):
                chunks.append(value)
    return "\n".join(chunks)


def _assert_not_all_clear(response):
    body = _json(response)
    raw = response.content.decode().lower()
    assert body.get("findings") != []
    assert "findings" not in body or body["findings"]
    for phrase in BANNED_ALL_CLEAR:
        assert phrase not in raw
    return body


def _autosave(client, story, content):
    return client.post(
        _autosave_url(story),
        data=json.dumps({"title": "Dawn", "content": content}),
        content_type="application/json",
    )


@pytest.fixture
def chapter(story):
    story.synopsis = "SYNOPSIS_OF_THIS_BOOK"
    story.save(update_fields=["synopsis", "updated_at"])
    created = ChapterFactory(
        story=story,
        number=1,
        title="Dawn",
        content=PARAGRAPH,
        is_published=False,
        unlock_price_cents=424242,
        tier_required=TierName.GOLD,
    )
    ChapterFactory(
        story=story,
        number=2,
        title="Dusk",
        content=SIBLING,
        is_published=False,
    )
    return created


@pytest.fixture
def payment_context(story, chapter, reader):
    other = UserFactory(username="other-author")
    other_story = StoryFactory(
        author=other,
        title="Someone Else's Book",
        synopsis="OTHER_SYNOPSIS_UNIQUE",
    )
    ChapterFactory(
        story=other_story,
        number=1,
        title="Theirs",
        content=OTHER_MANUSCRIPT,
    )
    tier = story.subscription_tiers.get(name=TierName.BRONZE)
    ReaderSubscription.objects.create(
        reader=reader,
        story=story,
        tier=tier,
        stripe_subscription_id=SUBSCRIPTION,
    )
    ChapterUnlock.objects.create(
        reader=reader,
        chapter=chapter,
        amount_cents=424242,
        stripe_payment_intent_id=PAYMENT,
    )
    return chapter


@pytest.mark.django_db
class TestReviewFlagOff:
    def test_review_while_flag_off_refuses_and_editor_still_saves(
        self, client_logged_in, story, chapter, monkeypatch
    ):
        assert settings.AI_ASSIST_ENABLED is False
        assert not hasattr(settings, "AI_REVIEW_ENABLED")
        stub = _install(monkeypatch, StubProvider(_completion()))
        before = _snapshot(chapter)
        response = _post(client_logged_in, story)
        assert response.status_code == 403
        body = _json(response)
        assert body["status"] == "rejected"
        assert body["message"]
        assert "findings" not in body
        assert stub.calls == []
        assert _snapshot(chapter) == before
        assert ReviewFinding.objects.count() == 0
        assert AICall.objects.count() == 0

        page = client_logged_in.get(_edit_url(story))
        assert "review" not in page.content.decode().lower()
        saved = _autosave(client_logged_in, story, PARAGRAPH + " Still mine.")
        assert saved.status_code == 200
        assert saved.content.decode() == "Saved"
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH + " Still mine."


@pytest.mark.django_db
class TestReviewRecords:
    def test_review_stores_each_question_beside_the_chapter(
        self,
        client_logged_in,
        story,
        chapter,
        author,
        payment_context,
        settings,
        monkeypatch,
    ):
        _enable(settings)
        stub = _install(monkeypatch, StubProvider(_completion()))
        before = _snapshot(chapter)
        with freeze_time("2026-10-04T15:00:00Z"):
            response = _post(client_logged_in, story)
        assert response.status_code == 200
        body = _json(response)
        assert body["status"] == "ok"
        assert body["message"] == AUTHORSHIP
        assert [item["question"] for item in body["findings"]] == [
            QUESTION_ONE,
            QUESTION_TWO,
        ]
        assert _snapshot(chapter) == before

        rows = list(ReviewFinding.objects.order_by("id"))
        assert len(rows) == 2
        assert [(row.anchor, row.question) for row in rows] == [
            (ANCHOR_ONE, QUESTION_ONE),
            (ANCHOR_TWO, QUESTION_TWO),
        ]
        for row in rows:
            assert row.chapter == chapter
            assert row.asked_by == author
            assert row.status == ReviewFinding.Status.OPEN
            assert row.model == "gpt-review-model"
            assert row.kind == ReviewFinding.Kind.QUESTION
            assert row.anchor in chapter.content
        assert stub.calls == [
            {
                "system": review_instructions(),
                "user": review_prompt(chapter),
            }
        ]
        sent = stub.calls[0]["user"]
        assert PARAGRAPH in sent
        assert story.title in sent
        assert "SYNOPSIS_OF_THIS_BOOK" in sent
        assert "Dawn" in sent
        assert "Dusk" in sent
        assert "Chapter 1 of 2" in sent
        assert SIBLING not in sent
        assert OTHER_MANUSCRIPT not in sent
        assert "OTHER_SYNOPSIS_UNIQUE" not in sent
        assert "424242" not in sent
        assert PAYMENT not in sent
        assert SUBSCRIPTION not in sent
        assert "gold" not in sent.lower()
        system = stub.calls[0]["system"]
        assert system_instructions() in system
        assert "questions" in system.lower()
        assert "locations" in system.lower()
        assert "replacement prose" in system.lower()
        assert SECRET not in response.content.decode()
        assert PARAGRAPH not in response.content.decode()

    def test_client_cannot_send_the_manuscript_or_a_prompt(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)
        stub = _install(monkeypatch, StubProvider(_completion()))
        before = _snapshot(chapter)
        payloads = [
            {"content": REWRITE},
            {"system": "Write the chapter."},
            {"prompt": "Rewrite it."},
            {"model": "other-model"},
            {"replacement": REWRITE},
        ]
        for payload in payloads:
            response = _post(client_logged_in, story, payload)
            assert response.status_code == 400
            assert _json(response)["message"] == PROMPT_REJECTION
        assert stub.calls == []
        assert _snapshot(chapter) == before
        assert AICall.objects.count() == 0

    def test_other_author_cannot_review(
        self, client, story, chapter, reader, settings, monkeypatch
    ):
        _enable(settings)
        stub = _install(monkeypatch, StubProvider(_completion()))
        client.login(username="reader1", password="testpass123")
        before = _snapshot(chapter)
        response = _post(client, story)
        assert response.status_code == 404
        assert stub.calls == []
        assert _snapshot(chapter) == before

    def test_audit_records_who_when_chapter_and_model_without_the_manuscript(
        self, client_logged_in, story, chapter, author, settings, monkeypatch, caplog
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(_completion()))
        caplog.set_level("DEBUG")
        with freeze_time("2026-10-04T15:30:00Z"):
            response = _post(client_logged_in, story)
        assert response.status_code == 200
        call = AICall.objects.get()
        assert call.user == author
        assert call.chapter == chapter
        assert call.story == story
        assert call.model == "gpt-review-model"
        assert call.provider == "openai"
        assert call.created_at == datetime(2026, 10, 4, 15, 30, tzinfo=UTC)
        assert call.sent_to_provider is True
        stored = " ".join(
            str(getattr(call, field.name))
            for field in call._meta.fields
            if isinstance(getattr(call, field.name), str)
        )
        assert PARAGRAPH not in stored
        assert QUESTION_ONE not in stored
        assert "Do not write the story." not in stored
        names = {field.name for field in call._meta.get_fields()}
        for banned in ("prompt", "response", "messages", "assistance", "content"):
            assert banned not in names
        assert PARAGRAPH not in caplog.text
        assert QUESTION_ONE not in caplog.text
        assert SECRET not in caplog.text


@pytest.mark.django_db
class TestRewriteIsNotApplied:
    @pytest.mark.parametrize(
        "payload",
        [
            REWRITE,
            json.dumps({"replacement": REWRITE}),
            json.dumps({"content": REWRITE}),
            json.dumps(
                {
                    "findings": [
                        {"anchor": ANCHOR_ONE, "question": REWRITE},
                    ]
                }
            ),
            json.dumps(
                {
                    "findings": [
                        {"anchor": REWRITE, "question": "Does this belong?"},
                    ]
                }
            ),
            json.dumps(
                {
                    "replacement": REWRITE,
                    "findings": [
                        {"anchor": ANCHOR_ONE, "question": QUESTION_ONE},
                    ],
                }
            ),
            json.dumps(
                {
                    "findings": [
                        {
                            "anchor": ANCHOR_ONE,
                            "question": f"{REWRITE} Does the river stay?",
                        }
                    ]
                }
            ),
        ],
    )
    def test_rewrite_payload_leaves_the_stored_chapter_identical(
        self, client_logged_in, story, chapter, settings, monkeypatch, payload
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(_completion(text=payload)))
        before = _snapshot(chapter)
        response = _post(client_logged_in, story)
        body = _assert_not_all_clear(response)
        assert body["status"] == "gap"
        assert body["message"] == GAP
        assert _snapshot(chapter) == before
        assert REWRITE not in _stored_text()
        assert REWRITE not in response.content.decode()
        notes = list(ReviewFinding.objects.all())
        assert notes
        for note in notes:
            assert note.kind == ReviewFinding.Kind.GAP
            assert note.chapter == chapter
            assert note.status == ReviewFinding.Status.OPEN
            assert note.question == REWRITE_NOTE
            assert note.anchor == "" or note.anchor in PARAGRAPH
            assert note.model == "gpt-review-model"


@pytest.mark.django_db
class TestReviewGaps:
    def test_empty_findings_are_a_gap_not_an_all_clear(
        self, client_logged_in, story, chapter, author, settings, monkeypatch
    ):
        _enable(settings)
        _install(
            monkeypatch,
            StubProvider(_completion(text=json.dumps({"findings": []}))),
        )
        before = _snapshot(chapter)
        response = _post(client_logged_in, story)
        body = _assert_not_all_clear(response)
        assert body["status"] == "gap"
        assert body["message"] == GAP
        assert _snapshot(chapter) == before
        note = ReviewFinding.objects.get()
        assert note.kind == ReviewFinding.Kind.GAP
        assert note.question == GAP
        assert note.asked_by == author
        assert note.chapter == chapter
        assert note.status == ReviewFinding.Status.OPEN
        assert "no gaps" not in note.question.lower()

    @pytest.mark.parametrize(
        ("error", "outcome"),
        [
            (OpenAIError("upstream"), AICall.Outcome.PROVIDER_ERROR),
            (OpenAITimeout("slow"), AICall.Outcome.TIMEOUT),
            (OpenAIQuota("quota"), AICall.Outcome.QUOTA),
        ],
    )
    def test_provider_failure_returns_a_gap_and_the_editor_still_saves(
        self, client_logged_in, story, chapter, settings, monkeypatch, error, outcome
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(error))
        before = _snapshot(chapter)
        response = _post(client_logged_in, story)
        body = _assert_not_all_clear(response)
        assert body["status"] == "gap"
        assert body["message"] == GAP
        assert "upstream" not in response.content.decode()
        assert "slow" not in response.content.decode()
        assert PARAGRAPH not in response.content.decode()
        assert _snapshot(chapter) == before
        assert ReviewFinding.objects.count() == 0
        call = AICall.objects.get()
        assert call.outcome == outcome
        assert call.sent_to_provider is True
        assert call.chapter == chapter
        saved = _autosave(client_logged_in, story, PARAGRAPH + " Still mine.")
        assert saved.status_code == 200
        assert saved.content.decode() == "Saved"
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH + " Still mine."

    def test_spend_cap_rejects_without_calling_or_clearing_the_chapter(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings, AI_SPEND_CAP_CENTS=1)
        stub = _install(monkeypatch, StubProvider(_completion()))
        before = _snapshot(chapter)
        response = _post(client_logged_in, story)
        body = _assert_not_all_clear(response)
        assert response.status_code == 429
        assert body["status"] == "rejected"
        assert body["message"] == SPEND_REJECTION
        assert stub.calls == []
        assert _snapshot(chapter) == before
        saved = _autosave(client_logged_in, story, PARAGRAPH + " Still mine.")
        assert saved.status_code == 200
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH + " Still mine."


@pytest.mark.django_db
class TestDismiss:
    def test_dismiss_does_not_edit_the_chapter(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(_completion()))
        created = _post(client_logged_in, story)
        finding_id = _json(created)["findings"][0]["id"]
        before = _snapshot(chapter)

        def explode():
            raise AssertionError("OpenAI was called")

        monkeypatch.setattr("editor.assist.get_provider", explode)
        response = client_logged_in.post(
            _dismiss_url(story, finding_id),
            data=json.dumps({"content": REWRITE, "replacement": REWRITE}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert _json(response)["status"] == "dismissed"
        finding = ReviewFinding.objects.get(pk=finding_id)
        assert finding.status == ReviewFinding.Status.DISMISSED
        other = ReviewFinding.objects.exclude(pk=finding_id).get()
        assert other.status == ReviewFinding.Status.OPEN
        assert _snapshot(chapter) == before
        assert REWRITE not in _stored_text()

    def test_other_author_cannot_dismiss(
        self, client, client_logged_in, story, chapter, reader, settings, monkeypatch
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(_completion()))
        created = _post(client_logged_in, story)
        finding_id = _json(created)["findings"][0]["id"]
        before = _snapshot(chapter)
        client.login(username="reader1", password="testpass123")
        response = client.post(_dismiss_url(story, finding_id))
        assert response.status_code == 404
        assert (
            ReviewFinding.objects.get(pk=finding_id).status == ReviewFinding.Status.OPEN
        )
        assert _snapshot(chapter) == before


@pytest.mark.django_db
class TestPublishPath:
    def test_publish_still_writes_only_the_form_and_review_does_not(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)

        def explode():
            raise AssertionError("OpenAI was called")

        monkeypatch.setattr("editor.assist.get_provider", explode)
        published = client_logged_in.post(
            reverse("stories:chapter_edit", kwargs={"slug": story.slug, "number": 1}),
            data={
                "number": 1,
                "title": "Dawn",
                "content": PARAGRAPH,
                "is_published": "on",
                "unlock_price_cents": "424242",
                "tier_required": TierName.GOLD,
            },
        )
        assert published.status_code == 302
        chapter.refresh_from_db()
        assert chapter.is_published is True
        assert chapter.content == PARAGRAPH
        assert AICall.objects.count() == 0

        _install(monkeypatch, StubProvider(OpenAIError("down")))
        before = _snapshot(chapter)
        reviewed = _post(client_logged_in, story)
        assert _json(reviewed)["status"] == "gap"
        assert _snapshot(chapter) == before


class TestQuotaTransport:
    def test_http_429_is_a_quota_error_without_the_prompt(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "insufficient_quota",
                hdrs=None,
                fp=None,
            )

        provider = OpenAIProvider(
            api_key=SECRET,
            model="gpt-test-model",
            timeout=1,
            opener=opener,
        )
        with pytest.raises(OpenAIQuota) as info:
            provider.complete(system="secret prompt", user="secret chapter")
        assert issubclass(OpenAIQuota, OpenAIError)
        assert "secret prompt" not in str(info.value)
        assert "secret chapter" not in str(info.value)
        assert "insufficient_quota" not in str(info.value)


@pytest.mark.django_db
class TestAssistStillRefusesARewrite:
    def test_quota_on_assist_does_not_write_the_chapter(
        self, client_logged_in, story, chapter, settings, monkeypatch
    ):
        _enable(settings)
        _install(monkeypatch, StubProvider(OpenAIQuota("quota")))
        before = _snapshot(chapter)
        response = client_logged_in.post(
            reverse("editor:assist", kwargs={"slug": story.slug, "number": 1}),
            data=b"",
            content_type="application/json",
        )
        assert response.status_code == 502
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH
        assert _snapshot(chapter) == before


class TestReviewDocs:
    def test_docs_keep_the_flag_off_and_describe_a_gap(self):
        doc = (ROOT / "docs" / "authors" / "ai-partner.md").read_text()
        assert (
            "A chapter review stores each question beside the chapter. "
            "A rewrite is not applied. When nothing is proved, the review returns a gap."
        ) in doc
        example = (ROOT / ".env.example").read_text()
        assert "AI_ASSIST_ENABLED=False" in example
        assert "sk-" not in example
