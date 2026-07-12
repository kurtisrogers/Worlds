"""Engagement views — comments and reactions."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from engagement.models import ChapterComment, ChapterReaction, ReactionType
from stories.models import Chapter


def _get_reaction_counts(chapter: Chapter) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reaction_type, _ in ReactionType.choices:
        counts[reaction_type] = chapter.reactions.filter(reaction_type=reaction_type).count()
    return counts


def _get_user_reaction(user, chapter: Chapter) -> str | None:
    if not user.is_authenticated:
        return None
    reaction = chapter.reactions.filter(user=user).first()
    return reaction.reaction_type if reaction else None


def chapter_engagement_context(request, chapter: Chapter) -> dict:
    return {
        "comments": chapter.comments.select_related("user").all()[:50],
        "reaction_counts": _get_reaction_counts(chapter),
        "user_reaction": _get_user_reaction(request.user, chapter),
        "reaction_types": ReactionType.choices,
    }


@login_required
@require_POST
def post_comment(request, slug, number):
    chapter = get_object_or_404(Chapter, story__slug=slug, number=number)
    body = request.POST.get("body", "").strip()
    if not body:
        return HttpResponse("Comment cannot be empty", status=400)

    ChapterComment.objects.create(chapter=chapter, user=request.user, body=body)

    return render(
        request,
        "engagement/partials/comments_list.html",
        {
            "chapter": chapter,
            "comments": chapter.comments.select_related("user").all()[:50],
            "story": chapter.story,
        },
    )


@login_required
@require_POST
def toggle_reaction(request, slug, number):
    chapter = get_object_or_404(Chapter, story__slug=slug, number=number)
    reaction_type = request.POST.get("reaction_type", ReactionType.LIKE)

    if reaction_type not in dict(ReactionType.choices):
        return HttpResponse("Invalid reaction", status=400)

    existing = ChapterReaction.objects.filter(chapter=chapter, user=request.user).first()
    if existing:
        if existing.reaction_type == reaction_type:
            existing.delete()
        else:
            existing.reaction_type = reaction_type
            existing.save(update_fields=["reaction_type"])
    else:
        ChapterReaction.objects.create(
            chapter=chapter,
            user=request.user,
            reaction_type=reaction_type,
        )

    return render(
        request,
        "engagement/partials/reactions_bar.html",
        {
            "chapter": chapter,
            "story": chapter.story,
            "reaction_counts": _get_reaction_counts(chapter),
            "user_reaction": _get_user_reaction(request.user, chapter),
            "reaction_types": ReactionType.choices,
        },
    )
