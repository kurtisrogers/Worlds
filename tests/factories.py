"""Shared test fixtures and factories."""

import factory
from django.contrib.auth.models import User

from accounts.models import AuthorProfile
from stories.models import Chapter, Story, StoryStatus, SubscriptionTier, TierName


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class AuthorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuthorProfile

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(lambda o: o.user.username)


class StoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Story

    author = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Story {n}")
    synopsis = "A compelling tale of adventure."
    status = StoryStatus.PUBLISHING


class ChapterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chapter

    story = factory.SubFactory(StoryFactory)
    number = factory.Sequence(lambda n: n + 1)
    title = factory.LazyAttribute(lambda o: f"Chapter {o.number}")
    content = "Once upon a time..."
    is_published = True


class SubscriptionTierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubscriptionTier

    story = factory.SubFactory(StoryFactory)
    name = TierName.BRONZE
    price_cents = 499
    description = "Bronze tier access"
    sort_order = 0
