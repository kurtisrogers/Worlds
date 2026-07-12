"""Chapter access control logic."""

from stories.models import Chapter, ReaderSubscription, TierName


TIER_RANK = {
    TierName.NONE: 0,
    TierName.BRONZE: 1,
    TierName.SILVER: 2,
    TierName.GOLD: 3,
}


def get_reader_tier_rank(user, story) -> int:
    """Return the highest active subscription tier rank for a reader on a story."""
    if not user.is_authenticated:
        return 0
    subscription = (
        ReaderSubscription.objects.filter(
            reader=user,
            story=story,
            status=ReaderSubscription.Status.ACTIVE,
        )
        .select_related("tier")
        .first()
    )
    if not subscription:
        return 0
    return TIER_RANK.get(subscription.tier.name, 0)


def can_read_chapter(user, chapter: Chapter) -> bool:
    """Determine if a user can read a chapter's full content."""
    if not chapter.is_published:
        if user.is_authenticated and chapter.story.author_id == user.id:
            return True
        return False

    if chapter.is_free:
        return True

    if not user.is_authenticated:
        return False

    if chapter.story.author_id == user.id:
        return True

    if chapter.unlock_price_cents:
        if chapter.unlocks.filter(reader=user).exists():
            return True

    required_rank = TIER_RANK.get(chapter.tier_required, 0)
    if required_rank > 0:
        reader_rank = get_reader_tier_rank(user, chapter.story)
        if reader_rank >= required_rank:
            return True

    return False


def get_access_reason(user, chapter: Chapter) -> str:
    """Human-readable reason why access is denied."""
    if can_read_chapter(user, chapter):
        return "granted"

    if not chapter.is_published:
        return "unpublished"

    if chapter.unlock_price_cents and chapter.tier_required != TierName.NONE:
        return "unlock_or_subscribe"

    if chapter.unlock_price_cents:
        return "unlock"

    if chapter.tier_required != TierName.NONE:
        return "subscribe"

    return "login_required"
