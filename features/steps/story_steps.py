"""Behave step definitions for Worlds platform."""

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
