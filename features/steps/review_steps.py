"""Behave steps for a chapter review. The provider is a stub, never live OpenAI."""

import json

from behave import given, then, when
from django.conf import settings
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

import editor.assist
from editor.models import ReviewFinding
from editor.openai_provider import Completion
from stories.models import Chapter

CHAPTER = (
    "The river kept its course through the quiet valley, "
    "and the morning stayed with that one sentence."
)
QUESTION = "Does the river stay in the valley?"
ANCHOR = "The river kept its course"


class StubProvider:
    def __init__(self):
        self.calls = []

    def complete(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        return Completion(
            text=json.dumps({"findings": [{"quote": ANCHOR, "question": QUESTION}]}),
            model="gpt-review-stub",
            input_tokens=3,
            output_tokens=3,
            usage_known=True,
        )


def _install(context):
    context._provider = editor.assist.get_provider
    context.review_stub = StubProvider()
    editor.assist.get_provider = lambda: context.review_stub


@given("the AI flag is on and the review model is stubbed")
def step_flag_on(context):
    context.ai_settings = override_settings(
        AI_ASSIST_ENABLED=True,
        WORLDS_ENVIRONMENT="local",
        OPENAI_API_KEY="sk-test-not-a-real-key",
        OPENAI_MODEL="gpt-test-model",
        OPENAI_TIMEOUT_SECONDS=30,
        AI_USER_RATE_LIMIT=None,
        AI_USER_RATE_WINDOW_SECONDS=None,
        AI_SPEND_CAP_CENTS=None,
        AI_SPEND_WINDOW_SECONDS=None,
        OPENAI_INPUT_CENTS_PER_MILLION_TOKENS=None,
        OPENAI_OUTPUT_CENTS_PER_MILLION_TOKENS=None,
    )
    context.ai_settings.enable()
    _install(context)


@given("the AI flag is off")
def step_flag_off(context):
    assert settings.AI_ASSIST_ENABLED is False
    _install(context)


@when("I open chapter {number:d} in the editor")
def step_open_editor(context, number):
    story = context.story
    context.chapter_number = number
    context.response = context.client.get(
        reverse("editor:edit", kwargs={"slug": story.slug, "number": number})
    )


@then("the editor offers Review")
def step_offers_review(context):
    html = context.response.content.decode()
    assert context.response.status_code == 200
    assert 'id="review-chapter"' in html
    assert ">Review<" in html


@then("the editor does not offer Review")
def step_no_review(context):
    html = context.response.content.decode()
    assert context.response.status_code == 200
    assert "review" not in html.lower()
    assert 'id="review-chapter"' not in html


@then("the editor has not called the model")
def step_not_called(context):
    assert context.review_stub.calls == []


@when("I run a review of chapter {number:d}")
def step_run_review(context, number):
    story = context.story
    context.response = context.client.post(
        reverse("editor:review", kwargs={"slug": story.slug, "number": number}),
        data=b"",
        content_type="application/json",
    )
    context.review_body = json.loads(context.response.content.decode())
    context.response = context.client.get(
        reverse("editor:edit", kwargs={"slug": story.slug, "number": number})
    )


@then('I see the finding "{question}"')
def step_see_finding(context, question):
    assert context.review_body["status"] == "ok"
    assert question in [item["question"] for item in context.review_body["findings"]]
    assert question.encode() in context.response.content
    assert b"no gaps" not in context.response.content.lower()


@then('chapter {number:d} still reads "{content}"')
def step_chapter_unchanged(context, number, content):
    chapter = Chapter.objects.get(story=context.story, number=number)
    assert chapter.content == content
    assert (
        content.encode()
        in context.client.get(
            reverse(
                "editor:edit",
                kwargs={"slug": context.story.slug, "number": number},
            )
        ).content
    )


@when("I dismiss that finding")
def step_dismiss(context):
    finding = ReviewFinding.objects.get(
        chapter__story=context.story,
        chapter__number=context.chapter_number,
        question=QUESTION,
        status=ReviewFinding.Status.OPEN,
    )
    context.client.post(
        reverse(
            "editor:dismiss",
            kwargs={
                "slug": context.story.slug,
                "number": context.chapter_number,
                "finding_id": finding.id,
            },
        )
    )
    context.response = context.client.get(
        reverse(
            "editor:edit",
            kwargs={
                "slug": context.story.slug,
                "number": context.chapter_number,
            },
        )
    )


@then('the editor no longer shows "{question}"')
def step_finding_gone(context, question):
    assert question.encode() not in context.response.content
    assert (
        ReviewFinding.objects.get(question=question).status
        == ReviewFinding.Status.DISMISSED
    )


@then("the review used the stubbed finding")
def step_stubbed(context):
    assert context.review_stub.calls
    finding = context.review_body["findings"][0]
    assert finding["question"] == QUESTION
    assert finding["quote"] == ANCHOR
    assert finding["anchor_status"] == "ok"
    assert finding["start_offset"] == 0
    user = User.objects.get(username=context.username)
    assert user.username == "alice"
    assert CHAPTER.split(",")[0] in context.review_stub.calls[0]["user"]
