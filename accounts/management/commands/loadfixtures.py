"""Load comprehensive fixture data for development and demos."""

import io

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.fixture_data import (
    AUTHORS,
    COMMENTS,
    DEMO_PASSWORD,
    FOLLOWS,
    LEGACY_USER_MAP,
    REACTIONS,
    READERS,
    SAVED_STORIES,
    STAFF,
    STORIES,
    SUBSCRIPTIONS,
    TRANSACTIONS,
    UNLOCKS,
)
from accounts.models import AuthorProfile, UserAccount
from accounts.roles import sync_django_staff_flags
from engagement.models import ChapterComment, ChapterReaction
from library.models import AuthorFollow, SavedStory
from payments.models import Transaction, TransactionStatus, TransactionType
from payments.services import calculate_fees, ensure_story_tiers
from stories.models import (
    Chapter,
    ChapterUnlock,
    ContentFormat,
    ContentSource,
    ReaderSubscription,
    Story,
    StoryStatus,
)


def _generate_cover(title: str, color: str) -> ContentFile:
    """Generate a simple placeholder cover image with Pillow."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 800, 1200
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)

    # Gradient overlay
    for y in range(height):
        alpha = int(80 * (y / height))
        draw.line([(0, y), (width, y)], fill=_darken(color, alpha))

    letter = title[0].upper() if title else "W"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 200)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), letter, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((width - text_w) / 2, (height - text_h) / 2 - 50),
        letter,
        fill="#ffffff",
        font=font,
    )

    # Title at bottom
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except OSError:
        title_font = font

    words = title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) > 18 and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    y_offset = height - 80 - len(lines) * 40
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        draw.text(((width - line_w) / 2, y_offset), line, fill="#f0e6d8", font=title_font)
        y_offset += 40

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    slug = title.lower().replace(" ", "-")[:40]
    return ContentFile(buffer.read(), name=f"{slug}-cover.png")


def _darken(hex_color: str, amount: int) -> str:
    hex_color = hex_color.lstrip("#")
    r = max(0, int(hex_color[0:2], 16) - amount)
    g = max(0, int(hex_color[2:4], 16) - amount)
    b = max(0, int(hex_color[4:6], 16) - amount)
    return f"#{r:02x}{g:02x}{b:02x}"


class Command(BaseCommand):
    help = "Load comprehensive fixture data (authors, stories, library, engagement)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing fixture users and their content before loading",
        )
        parser.add_argument(
            "--no-covers",
            action="store_true",
            help="Skip generating cover images",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            if options["flush"]:
                self._flush_fixture_data()

            users = self._create_users()
            stories = self._create_stories(users, skip_covers=options["no_covers"])
            self._create_library_data(users, stories)
            self._create_engagement(users, stories)
            self._create_transactions(users, stories)

        self._print_summary(users)

    def _flush_fixture_data(self):
        usernames = (
            [a["username"] for a in AUTHORS]
            + [r["username"] for r in READERS]
            + [s["username"] for s in STAFF]
            + list(LEGACY_USER_MAP.keys())
        )
        deleted, _ = User.objects.filter(username__in=usernames).delete()
        self.stdout.write(f"Flushed {deleted} existing fixture objects.")

    def _create_users(self) -> dict[str, User]:
        users: dict[str, User] = {}

        for author_data in AUTHORS:
            user, created = User.objects.get_or_create(
                username=author_data["username"],
                defaults={"email": author_data["email"]},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()

            profile, _ = AuthorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "display_name": author_data["display_name"],
                    "bio": author_data["bio"],
                    "stripe_account_id": author_data["stripe_account_id"],
                    "stripe_connect_onboarded": author_data["stripe_connect_onboarded"],
                },
            )
            users[author_data["username"]] = user

        for reader_data in READERS:
            user, created = User.objects.get_or_create(
                username=reader_data["username"],
                defaults={"email": reader_data["email"]},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[reader_data["username"]] = user

        for staff_data in STAFF:
            user, created = User.objects.get_or_create(
                username=staff_data["username"],
                defaults={"email": staff_data["email"]},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()

            account, _ = UserAccount.objects.get_or_create(user=user)
            account.platform_role = staff_data["platform_role"]
            account.save(update_fields=["platform_role", "updated_at"])
            sync_django_staff_flags(user)
            users[staff_data["username"]] = user

        # Legacy aliases for docs / backwards compatibility
        for legacy, canonical in LEGACY_USER_MAP.items():
            if canonical in users:
                legacy_user, created = User.objects.get_or_create(
                    username=legacy,
                    defaults={"email": f"{legacy}@worlds.example"},
                )
                if created:
                    legacy_user.set_password(DEMO_PASSWORD)
                    legacy_user.save()
                users[legacy] = legacy_user

        return users

    def _create_stories(self, users: dict[str, User], skip_covers: bool) -> dict[str, Story]:
        stories: dict[str, Story] = {}

        for story_data in STORIES:
            author = users[story_data["author"]]
            story, _ = Story.objects.update_or_create(
                title=story_data["title"],
                defaults={
                    "author": author,
                    "synopsis": story_data["synopsis"],
                    "status": story_data["status"],
                    "content_source": story_data["content_source"],
                },
            )

            if not skip_covers and story_data.get("cover_color"):
                cover = _generate_cover(story_data["title"], story_data["cover_color"])
                story.cover_image.save(cover.name, cover, save=True)

            ensure_story_tiers(story)
            stories[story.title] = story

            for ch in story_data["chapters"]:
                content_format = (
                    ContentFormat.HTML if ch.get("format") == "html" else ContentFormat.PLAIN
                )
                Chapter.objects.update_or_create(
                    story=story,
                    number=ch["number"],
                    defaults={
                        "title": ch["title"],
                        "content": ch["content"],
                        "content_format": content_format,
                        "is_published": ch.get("published", True),
                        "unlock_price_cents": ch.get("unlock_price_cents"),
                        "tier_required": ch.get("tier_required", "none"),
                    },
                )

        return stories

    def _create_library_data(self, users: dict[str, User], stories: dict[str, Story]):
        for reader_name, author_names in FOLLOWS.items():
            reader = users[reader_name]
            for author_name in author_names:
                AuthorFollow.objects.get_or_create(
                    follower=reader,
                    author=users[author_name],
                )

        for reader_name, story_titles in SAVED_STORIES.items():
            reader = users[reader_name]
            for title in story_titles:
                SavedStory.objects.get_or_create(user=reader, story=stories[title])

        for reader_name, subs in SUBSCRIPTIONS.items():
            reader = users[reader_name]
            for story_title, tier_name in subs:
                story = stories[story_title]
                tier = story.subscription_tiers.get(name=tier_name)
                ReaderSubscription.objects.update_or_create(
                    reader=reader,
                    story=story,
                    defaults={
                        "tier": tier,
                        "status": ReaderSubscription.Status.ACTIVE,
                        "stripe_subscription_id": f"sub_demo_{reader.id}_{story.id}",
                    },
                )

        for reader_name, unlocks in UNLOCKS.items():
            reader = users[reader_name]
            for story_title, chapter_number in unlocks:
                chapter = stories[story_title].chapters.get(number=chapter_number)
                ChapterUnlock.objects.get_or_create(
                    reader=reader,
                    chapter=chapter,
                    defaults={"amount_cents": chapter.unlock_price_cents or 0},
                )

    def _create_engagement(self, users: dict[str, User], stories: dict[str, Story]):
        for (story_title, chapter_number), comments in COMMENTS.items():
            chapter = stories[story_title].chapters.get(number=chapter_number)
            for comment_data in comments:
                ChapterComment.objects.get_or_create(
                    chapter=chapter,
                    user=users[comment_data["username"]],
                    defaults={"body": comment_data["body"]},
                )

        for (story_title, chapter_number), reactions in REACTIONS.items():
            chapter = stories[story_title].chapters.get(number=chapter_number)
            for reaction_data in reactions:
                ChapterReaction.objects.update_or_create(
                    chapter=chapter,
                    user=users[reaction_data["username"]],
                    defaults={"reaction_type": reaction_data["reaction_type"]},
                )

    def _create_transactions(self, users: dict[str, User], stories: dict[str, Story]):
        for tx_data in TRANSACTIONS:
            amount = tx_data["amount_cents"]
            fee, payout = calculate_fees(amount)
            tx_type = (
                TransactionType.SUBSCRIPTION
                if tx_data["type"] == "subscription"
                else TransactionType.CHAPTER_UNLOCK
            )
            Transaction.objects.get_or_create(
                user=users[tx_data["username"]],
                transaction_type=tx_type,
                amount_cents=amount,
                defaults={
                    "platform_fee_cents": fee,
                    "author_payout_cents": payout,
                    "status": TransactionStatus.COMPLETED,
                    "stripe_checkout_session_id": f"cs_demo_{tx_data['username']}_{amount}",
                    "metadata": {
                        "story_title": tx_data.get("story_title"),
                        "demo": True,
                    },
                },
            )

    def _print_summary(self, users: dict[str, User]):
        story_count = Story.objects.filter(
            author__username__in=[a["username"] for a in AUTHORS]
        ).count()
        chapter_count = Chapter.objects.filter(
            story__author__username__in=[a["username"] for a in AUTHORS]
        ).count()

        self.stdout.write(self.style.SUCCESS("\n✓ Fixture data loaded successfully!\n"))
        self.stdout.write(f"  Stories:       {story_count}")
        self.stdout.write(f"  Chapters:      {chapter_count}")
        self.stdout.write(f"  Saved books:   {SavedStory.objects.count()}")
        self.stdout.write(f"  Follows:       {AuthorFollow.objects.count()}")
        self.stdout.write(f"  Subscriptions: {ReaderSubscription.objects.count()}")
        self.stdout.write(f"  Comments:      {ChapterComment.objects.count()}")
        self.stdout.write(f"  Reactions:     {ChapterReaction.objects.count()}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Authors (password: demo1234):"))
        for author in AUTHORS:
            onboarded = "✓ payouts" if author["stripe_connect_onboarded"] else "○ payouts pending"
            self.stdout.write(f"  {author['username']:20} {author['display_name']:22} {onboarded}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Readers (password: demo1234):"))
        for reader in READERS:
            self.stdout.write(f"  {reader['username']}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Legacy aliases (same password):"))
        for legacy, canonical in LEGACY_USER_MAP.items():
            self.stdout.write(f"  {legacy} → maps to {canonical}")
        self.stdout.write("")
        self.stdout.write("  Browse: http://localhost:8000/discover/")
        self.stdout.write("  Library: http://localhost:8000/library/ (login as alex_reader)")
