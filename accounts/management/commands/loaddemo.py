"""Load demo data for development and testing."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import AuthorProfile
from payments.services import ensure_story_tiers
from stories.models import Chapter, Story, StoryStatus, TierName


class Command(BaseCommand):
    help = "Create demo users and a sample published story"

    def handle(self, *args, **options):
        author, created = User.objects.get_or_create(
            username="demo_author",
            defaults={"email": "author@worlds.example"},
        )
        if created:
            author.set_password("demo1234")
            author.save()

        AuthorProfile.objects.get_or_create(
            user=author,
            defaults={
                "display_name": "Elena Rivers",
                "bio": "Fantasy writer exploring worlds between dreams and reality.",
            },
        )

        reader, created = User.objects.get_or_create(
            username="demo_reader",
            defaults={"email": "reader@worlds.example"},
        )
        if created:
            reader.set_password("demo1234")
            reader.save()

        story, _ = Story.objects.get_or_create(
            title="The Starlight Chronicle",
            defaults={
                "author": author,
                "synopsis": (
                    "When the last lighthouse on the edge of the world begins to dim, "
                    "a young cartographer must chart a course through forgotten seas "
                    "to relight the stars themselves."
                ),
                "status": StoryStatus.PUBLISHING,
            },
        )
        ensure_story_tiers(story)

        chapters_data = [
            (
                1,
                "The Dimming Light",
                "The lighthouse had burned for three hundred years...",
                True,
                None,
                TierName.NONE,
            ),
            (
                2,
                "Charts of the Forgotten",
                "Maps, Mara discovered, were liars...",
                True,
                299,
                TierName.NONE,
            ),
            (
                3,
                "Silver Tides",
                "Only subscribers of Silver tier may read beyond this point...",
                True,
                None,
                TierName.SILVER,
            ),
        ]

        for number, title, content, published, price, tier in chapters_data:
            Chapter.objects.update_or_create(
                story=story,
                number=number,
                defaults={
                    "title": title,
                    "content": content,
                    "is_published": published,
                    "unlock_price_cents": price,
                    "tier_required": tier,
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully."))
        self.stdout.write("  Author: demo_author / demo1234")
        self.stdout.write("  Reader: demo_reader / demo1234")
        self.stdout.write(f'  Story:  "{story.title}" at /{story.slug}/')
