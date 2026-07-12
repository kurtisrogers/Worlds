"""In-app chapter editor views."""

import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from stories.models import Chapter, ContentSource, Story


@login_required
def editor(request, slug, number):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    chapters = story.chapters.all()

    return render(
        request,
        "editor/edit.html",
        {"story": story, "chapter": chapter, "chapters": chapters},
    )


@login_required
@require_POST
def autosave(request, slug, number):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    chapter.title = data.get("title", chapter.title)
    chapter.content = data.get("content", chapter.content)
    chapter.updated_at = timezone.now()
    chapter.save(update_fields=["title", "content", "updated_at"])

    story.content_source = ContentSource.EDITOR
    story.save(update_fields=["content_source", "updated_at"])

    if request.htmx:
        return HttpResponse(
            '<span class="text-emerald-400 text-sm">Saved</span>',
            headers={"HX-Trigger": "chapterSaved"},
        )
    return HttpResponse(json.dumps({"status": "saved"}), content_type="application/json")
