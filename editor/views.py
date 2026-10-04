"""In-app chapter editor views."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from editor.assist import PROMPT_REJECTION, run_assist
from editor.models import ReviewFinding
from editor.review import run_review
from stories.models import Chapter, ContentSource, Story

logger = logging.getLogger(__name__)

SAVING = "Saving"
SAVED = "Saved"
FAILED = "Failed"


def _plain(body, status):
    return HttpResponse(body, status=status, content_type="text/plain; charset=utf-8")


def _fields(request, chapter):
    content_type = (request.content_type or "").lower()
    if "json" in content_type:
        try:
            data = json.loads(request.body.decode("utf-8") or "null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
    else:
        data = request.POST

    title = data.get("title") if "title" in data else chapter.title
    content = data.get("content") if "content" in data else chapter.content
    if not isinstance(title, str) or not isinstance(content, str):
        return None
    return title, content


@login_required
def editor(request, slug, number):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    return render(
        request,
        "editor/edit.html",
        {
            "story": story,
            "chapter": chapter,
            "chapters": story.chapters.all(),
            "saving_label": SAVING,
            "saved_label": SAVED,
            "failed_label": FAILED,
        },
    )


@login_required
@require_POST
def autosave(request, slug, number):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    fields = _fields(request, chapter)
    if fields is None:
        return _plain(FAILED, 400)

    title, content = fields
    try:
        with transaction.atomic():
            chapter.title = title
            chapter.content = content
            chapter.updated_at = timezone.now()
            chapter.save(update_fields=["title", "content", "updated_at"])
            story.content_source = ContentSource.EDITOR
            story.save(update_fields=["content_source", "updated_at"])
    except Exception:
        logger.exception("Autosave failed for %s chapter %s", story.slug, number)
        return _plain(FAILED, 500)

    return _plain(SAVED, 200)


@login_required
@require_POST
def assist(request, slug, number):
    """Questions for one chapter. The model never writes the chapter."""
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    payload = _client_payload(request)
    if payload is None:
        return _assist_json(
            {"status": "rejected", "message": "The chapter text is unchanged."},
            400,
        )
    if payload:
        return _assist_json(
            {"status": "rejected", "message": PROMPT_REJECTION},
            400,
        )
    result = run_assist(user=request.user, chapter=chapter)
    return _assist_json(result.payload, result.status_code)


@login_required
@require_POST
def review(request, slug, number):
    """Store questions beside one chapter. The model never writes the chapter."""
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    payload = _client_payload(request)
    if payload is None:
        return _assist_json(
            {"status": "rejected", "message": "The chapter text is unchanged."},
            400,
        )
    if payload:
        return _assist_json(
            {"status": "rejected", "message": PROMPT_REJECTION},
            400,
        )
    result = run_review(user=request.user, chapter=chapter)
    return _assist_json(result.payload, result.status_code)


@login_required
@require_POST
def dismiss_finding(request, slug, number, finding_id):
    """Mark a finding dismissed. The chapter row is not saved."""
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    finding = get_object_or_404(ReviewFinding, pk=finding_id, chapter=chapter)
    if finding.status != ReviewFinding.Status.DISMISSED:
        finding.status = ReviewFinding.Status.DISMISSED
        finding.save(update_fields=["status"])
    return _assist_json({"status": "dismissed", "id": finding.id}, 200)


def _client_payload(request):
    """Empty body only. Any client field is an attempt to set the prompt."""
    raw = request.body or b""
    content_type = (request.content_type or "").lower()
    if "json" in content_type:
        if not raw.strip():
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return data
    return {
        key: value
        for key, value in request.POST.items()
        if key != "csrfmiddlewaretoken"
    }


def _assist_json(payload, status):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response
