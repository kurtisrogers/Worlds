"""Library views — Kindle-style reader collection."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from library.models import AuthorFollow, SavedStory
from library.services import toggle_author_follow, toggle_saved_story
from stories.models import ReaderSubscription, Story, StoryStatus

User = get_user_model()

VALID_TABS = ("all", "saved", "subscriptions", "following")


def _story_queryset():
    return Story.objects.filter(
        status__in=[StoryStatus.PUBLISHING, StoryStatus.PUBLISHED]
    ).select_related("author", "author__author_profile")


@login_required
def library(request):
    tab = request.GET.get("tab", "all")
    if tab not in VALID_TABS:
        tab = "all"

    all_stories = _story_queryset()
    saved_ids = list(SavedStory.objects.filter(user=request.user).values_list("story_id", flat=True))
    subscribed_ids = list(ReaderSubscription.objects.filter(
        reader=request.user,
        status=ReaderSubscription.Status.ACTIVE,
    ).values_list("story_id", flat=True))
    following_author_ids = list(AuthorFollow.objects.filter(
        follower=request.user
    ).values_list("author_id", flat=True))

    if tab == "saved":
        stories = all_stories.filter(id__in=saved_ids)
    elif tab == "subscriptions":
        stories = all_stories.filter(id__in=subscribed_ids)
    elif tab == "following":
        stories = all_stories.filter(author_id__in=following_author_ids)
    else:
        combined_ids = set(saved_ids) | set(subscribed_ids)
        stories_from_follows = all_stories.filter(author_id__in=following_author_ids)
        stories = (all_stories.filter(id__in=combined_ids) | stories_from_follows).distinct()

    story_meta = {}
    for story in stories:
        story_meta[story.id] = {
            "is_saved": story.id in saved_ids,
            "is_subscribed": story.id in subscribed_ids,
            "is_following_author": story.author_id in following_author_ids,
        }

    followed_authors = (
        User.objects.filter(id__in=following_author_ids)
        .select_related("author_profile")
        .order_by("username")
    )

    return render(
        request,
        "library/index.html",
        {
            "tab": tab,
            "stories": stories,
            "story_meta": story_meta,
            "followed_authors": followed_authors,
            "saved_count": len(saved_ids),
            "subscription_count": len(subscribed_ids),
            "following_count": len(following_author_ids),
        },
    )


@login_required
def toggle_save(request, slug):
    story = get_object_or_404(Story, slug=slug)
    now_saved = toggle_saved_story(request.user, story)

    if request.htmx:
        return render(
            request,
            "library/partials/save_button.html",
            {"story": story, "is_saved": now_saved},
        )

    message = f'"{story.title}" added to your library.' if now_saved else f'"{story.title}" removed from your library.'
    messages.success(request, message)
    return redirect("stories:detail", slug=slug)


@login_required
def toggle_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author == request.user:
        return HttpResponse("Cannot follow yourself", status=400)

    now_following = toggle_author_follow(request.user, author)

    if request.htmx:
        return render(
            request,
            "library/partials/follow_button.html",
            {"author": author, "is_following": now_following},
        )

    name = getattr(getattr(author, "author_profile", None), "name", author.username)
    message = f"You are now following {name}." if now_following else f"You unfollowed {name}."
    messages.success(request, message)
    next_url = request.GET.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("library:author", username=username)


def author_profile(request, username):
    author = get_object_or_404(
        User.objects.select_related("author_profile"),
        username=username,
    )
    stories = Story.objects.filter(
        author=author,
        status__in=[StoryStatus.PUBLISHING, StoryStatus.PUBLISHED],
    ).select_related("author", "author__author_profile")

    is_following = False
    saved_ids: set[int] = set()
    subscribed_ids: set[int] = set()
    if request.user.is_authenticated:
        is_following = AuthorFollow.objects.filter(
            follower=request.user, author=author
        ).exists()
        saved_ids = set(
            SavedStory.objects.filter(user=request.user, story__in=stories).values_list(
                "story_id", flat=True
            )
        )
        subscribed_ids = set(
            ReaderSubscription.objects.filter(
                reader=request.user,
                story__in=stories,
                status=ReaderSubscription.Status.ACTIVE,
            ).values_list("story_id", flat=True)
        )

    follower_count = AuthorFollow.objects.filter(author=author).count()

    story_meta = {}
    for story in stories:
        story_meta[story.id] = {
            "is_saved": story.id in saved_ids,
            "is_subscribed": story.id in subscribed_ids,
            "is_following_author": is_following,
        }

    return render(
        request,
        "library/author.html",
        {
            "author": author,
            "stories": stories,
            "is_following": is_following,
            "story_meta": story_meta,
            "follower_count": follower_count,
        },
    )
