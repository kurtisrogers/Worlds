"""In-app chapter editor views."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

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
