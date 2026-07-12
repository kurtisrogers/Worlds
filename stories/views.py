"""Story views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from library.services import get_user_subscription, is_following_author, is_story_saved
from payments.services import (
    create_chapter_checkout_session,
    create_subscription_checkout_session,
)
from stories.access import can_read_chapter, get_access_reason
from stories.forms import ChapterForm, StoryForm
from stories.models import Chapter, Story, StoryStatus


def home(request):
    stories = (
        Story.objects.filter(status__in=[StoryStatus.PUBLISHING, StoryStatus.PUBLISHED])
        .select_related("author", "author__author_profile")
        .prefetch_related("chapters")[:12]
    )
    return render(request, "stories/home.html", {"stories": stories, "empty_dict": {}})


def story_detail(request, slug):
    story = get_object_or_404(
        Story.objects.select_related("author__author_profile").prefetch_related(
            "chapters", "subscription_tiers"
        ),
        slug=slug,
    )
    chapters = story.chapters.filter(is_published=True)
    if request.user.is_authenticated and request.user == story.author:
        chapters = story.chapters.all()

    chapter_access = {
        ch.id: {
            "can_read": can_read_chapter(request.user, ch),
            "reason": get_access_reason(request.user, ch),
        }
        for ch in chapters
    }

    user_subscription = get_user_subscription(request.user, story)
    return render(
        request,
        "stories/detail.html",
        {
            "story": story,
            "chapters": chapters,
            "chapter_access": chapter_access,
            "is_saved": is_story_saved(request.user, story),
            "is_following_author": is_following_author(request.user, story.author),
            "user_subscription": user_subscription,
        },
    )


def chapter_read(request, slug, number):
    story = get_object_or_404(Story, slug=slug)
    chapter = get_object_or_404(Chapter, story=story, number=number)
    has_access = can_read_chapter(request.user, chapter)
    reason = get_access_reason(request.user, chapter)

    prev_chapter = (
        story.chapters.filter(number__lt=number, is_published=True)
        .order_by("-number")
        .first()
    )
    next_chapter = (
        story.chapters.filter(number__gt=number, is_published=True)
        .order_by("number")
        .first()
    )

    if request.htmx and not has_access:
        return render(
            request,
            "stories/partials/unlock_prompt.html",
            {"chapter": chapter, "reason": reason, "story": story},
        )

    return render(
        request,
        "stories/chapter.html",
        {
            "story": story,
            "chapter": chapter,
            "has_access": has_access,
            "reason": reason,
            "prev_chapter": prev_chapter,
            "next_chapter": next_chapter,
        },
    )


@login_required
def dashboard(request):
    stories = Story.objects.filter(author=request.user).prefetch_related("chapters")
    return render(request, "stories/dashboard.html", {"stories": stories})


@login_required
def story_create(request):
    if request.method == "POST":
        form = StoryForm(request.POST, request.FILES)
        if form.is_valid():
            story = form.save(commit=False)
            story.author = request.user
            story.save()
            from payments.services import ensure_story_tiers

            ensure_story_tiers(story)
            messages.success(
                request, f'"{story.title}" created! Add your first chapter.'
            )
            return redirect("stories:manage", slug=story.slug)
    else:
        form = StoryForm()
    return render(request, "stories/story_form.html", {"form": form, "is_create": True})


@login_required
def story_manage(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapters = story.chapters.all()
    tiers = story.subscription_tiers.all()

    if request.method == "POST" and request.POST.get("action") == "upload_cover":
        if request.FILES.get("cover_image"):
            story.cover_image = request.FILES["cover_image"]
            story.save(update_fields=["cover_image", "updated_at"])
            messages.success(request, "Cover art updated.")
        return redirect("stories:manage", slug=story.slug)

    return render(
        request,
        "stories/manage.html",
        {"story": story, "chapters": chapters, "tiers": tiers},
    )


@login_required
def story_edit(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    if request.method == "POST":
        form = StoryForm(request.POST, request.FILES, instance=story)
        if form.is_valid():
            form.save()
            messages.success(request, "Story updated.")
            return redirect("stories:manage", slug=story.slug)
    else:
        form = StoryForm(instance=story)
    return render(
        request,
        "stories/story_form.html",
        {"form": form, "story": story, "is_create": False},
    )


@login_required
def chapter_create(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    next_number = (
        story.chapters.order_by("-number").values_list("number", flat=True).first() or 0
    ) + 1

    if request.method == "POST":
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.story = story
            chapter.save()
            messages.success(request, f"Chapter {chapter.number} saved.")
            if request.htmx:
                return render(
                    request,
                    "stories/partials/chapter_row.html",
                    {"chapter": chapter, "story": story},
                )
            return redirect("editor:edit", slug=story.slug, number=chapter.number)
    else:
        form = ChapterForm(initial={"number": next_number})

    return render(
        request,
        "stories/chapter_form.html",
        {"form": form, "story": story, "is_create": True},
    )


@login_required
def chapter_edit(request, slug, number):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    chapter = get_object_or_404(Chapter, story=story, number=number)

    if request.method == "POST":
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.success(request, "Chapter updated.")
            return redirect("stories:manage", slug=story.slug)
    else:
        form = ChapterForm(instance=chapter)

    return render(
        request,
        "stories/chapter_form.html",
        {"form": form, "story": story, "chapter": chapter, "is_create": False},
    )


@login_required
def unlock_chapter(request, slug, number):
    story = get_object_or_404(Story, slug=slug)
    chapter = get_object_or_404(Chapter, story=story, number=number)

    if can_read_chapter(request.user, chapter):
        return redirect("stories:chapter", slug=slug, number=number)

    url = create_chapter_checkout_session(request.user, chapter, request)
    if url:
        return redirect(url)
    messages.error(request, "Unable to create checkout session.")
    return redirect("stories:chapter", slug=slug, number=number)


@login_required
def subscribe_tier(request, slug, tier_name):
    story = get_object_or_404(Story, slug=slug)
    tier = get_object_or_404(story.subscription_tiers, name=tier_name)

    url = create_subscription_checkout_session(request.user, tier, request)
    if url:
        return redirect(url)
    messages.error(request, "Unable to create subscription session.")
    return redirect("stories:detail", slug=slug)


def discover(request):
    query = request.GET.get("q", "")
    stories = Story.objects.filter(
        status__in=[StoryStatus.PUBLISHING, StoryStatus.PUBLISHED]
    ).select_related("author", "author__author_profile")
    if query:
        stories = stories.filter(
            Q(title__icontains=query) | Q(synopsis__icontains=query)
        )
    return render(
        request,
        "stories/discover.html",
        {"stories": stories, "query": query, "empty_dict": {}},
    )
