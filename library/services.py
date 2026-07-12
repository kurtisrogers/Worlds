"""Library helper functions."""

from django.contrib.auth import get_user_model

from library.models import AuthorFollow, SavedStory
from stories.models import ReaderSubscription, Story

User = get_user_model()


def is_story_saved(user, story: Story) -> bool:
    if not user.is_authenticated:
        return False
    return SavedStory.objects.filter(user=user, story=story).exists()


def is_following_author(user, author: User) -> bool:
    if not user.is_authenticated or user == author:
        return False
    return AuthorFollow.objects.filter(follower=user, author=author).exists()


def get_user_subscription(user, story: Story):
    if not user.is_authenticated:
        return None
    return (
        ReaderSubscription.objects.filter(
            reader=user,
            story=story,
            status=ReaderSubscription.Status.ACTIVE,
        )
        .select_related("tier")
        .first()
    )


def toggle_saved_story(user, story: Story) -> bool:
    """Toggle save state. Returns True if now saved."""
    saved, created = SavedStory.objects.get_or_create(user=user, story=story)
    if not created:
        saved.delete()
        return False
    return True


def toggle_author_follow(user, author: User) -> bool:
    """Toggle follow state. Returns True if now following."""
    if user == author:
        return False
    follow, created = AuthorFollow.objects.get_or_create(follower=user, author=author)
    if not created:
        follow.delete()
        return False
    return True
