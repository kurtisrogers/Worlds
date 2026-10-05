"""Ask for questions about one stored chapter. Never write the chapter."""

import json
import logging
import re

from django.conf import settings
from django.db import transaction

from editor import assist
from editor.anchors import place_quote, present_finding
from editor.models import AICall, ReviewFinding
from editor.openai_provider import OpenAIError, OpenAIQuota, OpenAITimeout
from editor.policy import review_instructions, review_prompt

logger = logging.getLogger(__name__)

NO_QUESTIONS = "No questions this time. Your chapter hasn't changed."
DID_NOT_RUN = "The review did not run. Your chapter hasn't changed."
NOTHING_TO_REVIEW = "There's nothing to review yet."
REWRITE_NOTE = "The model returned replacement prose. Nothing was applied."
_MAX_QUESTION = 400
_MAX_NOVEL = 80
_LONG_QUESTION = 80
_QUOTE = 12
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_REWRITE_KEYS = frozenset(
    {
        "replacement",
        "rewrite",
        "rewritten",
        "revised",
        "revised_text",
        "new_text",
        "new_chapter",
        "prose",
        "manuscript",
        "content",
        "chapter_text",
        "suggestion",
        "replace",
        "draft",
        "confirmation",
    }
)


class ReviewResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload


def run_review(*, user, chapter):
    """Store questions beside the chapter. The chapter row is not saved.

    A review that stores questions marks this chapter's earlier open
    findings superseded. Dismissed findings stay dismissed. A provider
    failure stores nothing and supersedes nothing. An empty chapter
    does not call the provider, does not write an audit row, and does
    not supersede findings.
    """
    refused = assist.refusal(user)
    if refused is not None:
        return ReviewResponse(refused.status_code, refused.payload)

    if _chapter_is_empty(chapter):
        return ReviewResponse(
            200,
            {
                "status": "empty",
                "state": "empty",
                "message": NOTHING_TO_REVIEW,
            },
        )

    call = AICall.objects.create(
        user=user,
        story=chapter.story,
        chapter=chapter,
        model=settings.OPENAI_MODEL,
        provider="openai",
        outcome=AICall.Outcome.PROVIDER_ERROR,
        sent_to_provider=True,
    )
    try:
        completion = assist.get_provider().complete(
            system=review_instructions(),
            user=review_prompt(chapter),
        )
    except OpenAITimeout:
        return _finish(call, AICall.Outcome.TIMEOUT, 502)
    except OpenAIQuota:
        return _finish(call, AICall.Outcome.QUOTA, 429)
    except OpenAIError:
        return _finish(call, AICall.Outcome.PROVIDER_ERROR, 502)
    except Exception:
        return _finish(call, AICall.Outcome.PROVIDER_ERROR, 502)

    model = completion.model or call.model
    call.model = model
    call.input_tokens = completion.input_tokens
    call.output_tokens = completion.output_tokens
    call.cost_cents = assist._cost_cents(completion, assist._spend_cap())
    questions, note = _interpret(completion.text or "", chapter.content)
    if questions:
        call.outcome = AICall.Outcome.SUCCESS
        _save_call(call)
        _log(call)
        rows = _store_questions(
            chapter=chapter, user=user, model=model, pairs=questions
        )
        return ReviewResponse(
            200,
            {
                "status": "ok",
                "state": "ran",
                "message": assist.AUTHORSHIP,
                "findings": [present_finding(row, chapter.content) for row in rows],
            },
        )

    call.outcome = AICall.Outcome.EMPTY
    _save_call(call)
    _log(call)
    gap = _store_gap(chapter=chapter, user=user, model=model, question=note)
    return ReviewResponse(
        200,
        {
            "status": "gap",
            "state": "ran",
            "message": NO_QUESTIONS,
            "gap_note": present_finding(gap, chapter.content),
        },
    )


def _finish(call, outcome, status_code):
    call.outcome = outcome
    call.save(update_fields=["outcome"])
    _log(call)
    return ReviewResponse(
        status_code,
        {"status": "gap", "state": "failed", "message": DID_NOT_RUN},
    )


def _save_call(call):
    call.save(
        update_fields=[
            "outcome",
            "model",
            "input_tokens",
            "output_tokens",
            "cost_cents",
        ]
    )


def _log(call):
    logger.info(
        "AI call outcome=%s user=%s story=%s chapter=%s model=%s",
        call.outcome,
        call.user_id,
        call.story_id,
        call.chapter_id,
        call.model,
    )


def _chapter_is_empty(chapter):
    return not (chapter.content or "").strip()


def _supersede_open(chapter):
    """Mark this chapter's open findings superseded. Dismissed stay put."""
    chapter.review_findings.filter(status=ReviewFinding.Status.OPEN).update(
        status=ReviewFinding.Status.SUPERSEDED
    )


def _store_questions(*, chapter, user, model, pairs):
    with transaction.atomic():
        _supersede_open(chapter)
        return [
            ReviewFinding.objects.create(
                chapter=chapter,
                asked_by=user,
                anchor=quote or "",
                quote=quote,
                start_offset=offset,
                question=question,
                status=ReviewFinding.Status.OPEN,
                model=model,
                kind=ReviewFinding.Kind.QUESTION,
            )
            for quote, offset, question in pairs
        ]


def _store_gap(*, chapter, user, model, question):
    return ReviewFinding.objects.create(
        chapter=chapter,
        asked_by=user,
        anchor="",
        quote=None,
        start_offset=None,
        question=question,
        status=ReviewFinding.Status.OPEN,
        model=model,
        kind=ReviewFinding.Kind.GAP,
    )


def _interpret(text, chapter_content):
    """Return question pairs, or a gap note that does not contain model prose."""
    stripped = text.strip()
    if not stripped:
        return [], NO_QUESTIONS
    payload = _load_json(stripped)
    if payload is None or _contains_rewrite_key(payload):
        return [], REWRITE_NOTE
    if not isinstance(payload, dict) or set(payload) != {"findings"}:
        return [], REWRITE_NOTE
    items = payload["findings"]
    if not isinstance(items, list):
        return [], REWRITE_NOTE
    if not items:
        return [], NO_QUESTIONS
    pairs = []
    for item in items:
        parsed = _question(item, chapter_content)
        if parsed is None:
            return [], REWRITE_NOTE
        pairs.append(parsed)
    return pairs, ""


def _load_json(text):
    raw = text.strip()
    fenced = _FENCE.match(raw)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _contains_rewrite_key(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _REWRITE_KEYS or _contains_rewrite_key(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_rewrite_key(item) for item in value)
    return False


def _question(item, chapter_content):
    if not isinstance(item, dict) or set(item) != {"quote", "question"}:
        return None
    quote = item["quote"]
    question = item["question"]
    if not isinstance(quote, str) or not isinstance(question, str):
        return None
    question = question.strip()
    if (
        "?" not in question
        or "." in question
        or "\n" in question
        or not question
        or len(question) > _MAX_QUESTION
        or _novel_span(question, chapter_content) > _MAX_NOVEL
        or _rewrites_the_chapter(question, chapter_content)
    ):
        return None
    stored, offset = place_quote(chapter_content, quote.strip())
    return stored, offset, question


def _rewrites_the_chapter(question, chapter_content):
    """A long question that is mostly the chapter with words swapped is a rewrite."""
    if len(question) < _LONG_QUESTION:
        return False
    return _quoted_coverage(question, chapter_content) >= 0.45


def _novel_span(question, chapter_content):
    """Longest stretch that is not a quote from the chapter."""
    best = 0
    index = 0
    length = len(question)
    while index < length:
        quote = _quote_at(question, chapter_content, index)
        if quote:
            index += quote
            continue
        end = index + 1
        while end < length and not _quote_at(question, chapter_content, end):
            end += 1
        best = max(best, end - index)
        index = end
    return best


def _quoted_coverage(question, chapter_content):
    if not question:
        return 0
    covered = 0
    index = 0
    while index < len(question):
        quote = _quote_at(question, chapter_content, index)
        if quote:
            covered += quote
            index += quote
        else:
            index += 1
    return covered / len(question)


def _quote_at(question, chapter_content, index):
    limit = min(len(question) - index, 120)
    for size in range(limit, _QUOTE - 1, -1):
        if question[index : index + size] in chapter_content:
            return size
    return 0
