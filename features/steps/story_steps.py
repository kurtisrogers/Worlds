"""Behave step definitions for Worlds platform."""

import json

from behave import given, then, when
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from payments.services import ensure_story_tiers
from stories.models import Chapter, Story, StoryStatus, TierName


def get_client(context):
    if not hasattr(context, "client"):
        context.client = Client()
    return context.client


@given("I am on the home page")
def step_home_page(context):
    context.response = get_client(context).get(reverse("stories:home"))


@when('I register as "{username}" with password "{password}"')
def step_register(context, username, password):
    context.response = get_client(context).post(
        reverse("accounts:register"),
        {"username": username, "password1": password, "password2": password},
    )
    context.username = username
    context.password = password


@given('I am logged in as "{username}" with password "{password}"')
def step_login(context, username, password):
    client = get_client(context)
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username=username, password=password)
    client.login(username=username, password=password)
    context.username = username


@when('I create a story titled "{title}" with synopsis "{synopsis}"')
def step_create_story(context, title, synopsis):
    context.response = get_client(context).post(
        reverse("stories:create"),
        {
            "title": title,
            "synopsis": synopsis,
            "status": "draft",
            "content_source": "editor",
        },
    )
    context.story_title = title


@given('I have a story "{title}"')
def step_have_story(context, title):
    user = User.objects.get(username=context.username)
    story, _ = Story.objects.get_or_create(
        title=title,
        defaults={"author": user, "synopsis": "Test synopsis"},
    )
    ensure_story_tiers(story)
    context.story = story


@when('I add chapter {number:d} titled "{title}" with content "{content}"')
def step_add_chapter(context, number, title, content):
    story = context.story
    Chapter.objects.update_or_create(
        story=story,
        number=number,
        defaults={"title": title, "content": content, "is_published": True},
    )


@then('I should see "{text}" on my dashboard')
def step_see_on_dashboard(context, text):
    response = get_client(context).get(reverse("stories:dashboard"))
    assert text.encode() in response.content


@then('I should see "{text}"')
def step_should_see(context, text):
    assert text.encode() in context.response.content


@then("chapter {number:d} should be readable on the story page")
def step_chapter_readable(context, number):
    story = context.story
    response = get_client(context).get(
        reverse("stories:chapter", kwargs={"slug": story.slug, "number": number})
    )
    chapter = story.chapters.get(number=number)
    assert chapter.content.encode() in response.content


@given('a published story "{title}" with a free chapter {number:d}')
def step_published_free_chapter(context, title, number):
    user = User.objects.create_user(username=f"author_{title}", password="pass")
    story = Story.objects.create(
        author=user,
        title=title,
        synopsis="Test",
        status=StoryStatus.PUBLISHING,
    )
    Chapter.objects.create(
        story=story,
        number=number,
        title=f"Chapter {number}",
        content="Free chapter content for all readers.",
        is_published=True,
    )
    context.story = story


@when('I visit chapter {number:d} of "{title}"')
def step_visit_chapter(context, number, title):
    story = Story.objects.get(title=title)
    context.response = get_client(context).get(
        reverse("stories:chapter", kwargs={"slug": story.slug, "number": number})
    )


@then("I should see the chapter content")
def step_see_chapter_content(context):
    story = context.story
    chapter = story.chapters.first()
    assert chapter.content.encode() in context.response.content


@given('a published story "{title}" with a silver-tier chapter {number:d}')
def step_silver_tier_chapter(context, title, number):
    user = User.objects.create_user(username=f"author_{title}", password="pass")
    story = Story.objects.create(
        author=user,
        title=title,
        synopsis="Test",
        status=StoryStatus.PUBLISHING,
    )
    ensure_story_tiers(story)
    Chapter.objects.create(
        story=story,
        number=number,
        title=f"Chapter {number}",
        content="Premium silver content.",
        is_published=True,
        tier_required=TierName.SILVER,
    )
    context.story = story


@when('I save "{title}" to my library')
def step_save_to_library(context, title):
    from library.models import SavedStory

    story = Story.objects.get(title=title)
    user = User.objects.get(username=context.username)
    SavedStory.objects.get_or_create(user=user, story=story)


@then('I should see "{title}" in my saved library')
def step_see_in_saved_library(context, title):
    response = get_client(context).get(reverse("library:index"), {"tab": "saved"})
    assert title.encode() in response.content


@when('I follow the author of "{title}"')
def step_follow_author_of_story(context, title):
    from library.models import AuthorFollow

    story = Story.objects.get(title=title)
    user = User.objects.get(username=context.username)
    AuthorFollow.objects.get_or_create(follower=user, author=story.author)
    context.followed_author = story.author


@then("I should be following that author")
def step_following_author(context):
    response = get_client(context).get(
        reverse("library:author", kwargs={"username": context.followed_author.username})
    )
    assert b"Following" in response.content


def _reader_client(username):
    user, _created = User.objects.get_or_create(username=username)
    user.set_password("readerpass123")
    user.save(update_fields=["password"])
    client = Client()
    client.login(username=username, password="readerpass123")
    return client


def _story_by_title(title):
    return Story.objects.get(title=title)


@given('chapter {number:d} of "{title}" is released')
def step_chapter_released(context, number, title):
    story = _story_by_title(title)
    Chapter.objects.update_or_create(
        story=story,
        number=number,
        defaults={
            "title": f"Chapter {number}",
            "content": "Released chapter text.",
            "is_published": True,
        },
    )


@given('chapter {number:d} of "{title}" is a draft')
def step_chapter_draft(context, number, title):
    story = _story_by_title(title)
    Chapter.objects.update_or_create(
        story=story,
        number=number,
        defaults={
            "title": f"Chapter {number}",
            "content": "Draft chapter text.",
            "is_published": False,
        },
    )


@when('a reader "{username}" records a read of chapter {number:d} of "{title}"')
def step_reader_records_read(context, username, number, title):
    story = _story_by_title(title)
    _reader_client(username).post(
        reverse(
            "stories:record_read",
            kwargs={"slug": story.slug, "number": number},
        )
    )


@when('a reader "{username}" likes chapter {number:d} of "{title}"')
def step_reader_likes_chapter(context, username, number, title):
    story = _story_by_title(title)
    _reader_client(username).post(
        reverse(
            "stories:chapter_like",
            kwargs={"slug": story.slug, "number": number},
        )
    )


@when('I request the chapter counts for "{title}"')
def step_request_counts(context, title):
    story = _story_by_title(title)
    context.response = get_client(context).get(
        reverse("stories:chapter_counts", kwargs={"slug": story.slug})
    )
    context.counts = json.loads(context.response.content.decode())


@then(
    "chapter {number:d} counts are {reads:d} reads, {likes:d} likes, "
    "and {favourites:d} favourites"
)
def step_chapter_counts(context, number, reads, likes, favourites):
    matches = [row for row in context.counts["chapters"] if row["number"] == number]
    assert matches == [
        {
            "number": number,
            "reads": reads,
            "likes": likes,
            "favourites": favourites,
        }
    ]


@then("the counts do not include chapter {number:d}")
def step_counts_omit_chapter(context, number):
    assert all(row["number"] != number for row in context.counts["chapters"])


@then('the counts do not name "{username}"')
def step_counts_do_not_name(context, username):
    assert username not in context.response.content.decode()
