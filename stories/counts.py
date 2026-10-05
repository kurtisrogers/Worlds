"""Author counts and reader engagement for released chapters.

These views write engagement rows only. They do not save chapter text,
autosave fields, or publish state.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from stories.engagement import (
    record_chapter_read,
    released_chapter_counts,
    set_chapter_favourite,
    set_chapter_like,
)
from stories.models import Chapter, Story

_COUNT_KEYS = ("number", "reads", "likes", "favourites")


def _released_chapter(slug, number):
    story = get_object_or_404(Story, slug=slug)
    return get_object_or_404(Chapter, story=story, number=number, is_published=True)


def _json(payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


@login_required
@require_GET
def chapter_counts(request, slug):
    """Counts for the signed-in author's own released chapters."""
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapters = []
    for row in released_chapter_counts(story):
        chapters.append({key: row[key] for key in _COUNT_KEYS})
    return _json({"chapters": chapters})


@login_required
@require_POST
def record_read(request, slug, number):
    """Record one read of a released chapter. Repeating it changes nothing."""
    chapter = _released_chapter(slug, number)
    record_chapter_read(request.user, chapter)
    return _json({"recorded": True})


@login_required
@require_http_methods(["POST", "DELETE"])
def chapter_like(request, slug, number):
    """Like (POST) or unlike (DELETE) a released chapter. Both are idempotent."""
    chapter = _released_chapter(slug, number)
    liked = request.method == "POST"
    set_chapter_like(request.user, chapter, liked=liked)
    return _json({"liked": liked})


@login_required
@require_http_methods(["POST", "DELETE"])
def chapter_favourite(request, slug, number):
    """Favourite (POST) or unfavourite (DELETE). Both are idempotent."""
    chapter = _released_chapter(slug, number)
    favourited = request.method == "POST"
    set_chapter_favourite(request.user, chapter, favourited=favourited)
    return _json({"favourited": favourited})
