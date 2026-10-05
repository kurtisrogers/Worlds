"""Counts stored beside a story.

Reads, likes, and favourites live in their own tables. Nothing here saves
a chapter, so title, text, autosave, and publish state stay as they were.

A read is stored once per signed-in reader per released chapter
(``Chapter.is_published``). Repeating the record does not add another row.
Anonymous opens are not stored. A draft is refused and stores nothing.
"""

from django.db.models import Count

from stories.models import Chapter, ChapterFavourite, ChapterLike, ChapterRead


def record_chapter_read(reader, chapter) -> bool:
    """Record one read. False when the chapter is not released."""
    if not chapter.is_published:
        return False
    ChapterRead.objects.get_or_create(reader=reader, chapter=chapter)
    return True


def set_chapter_like(reader, chapter, *, liked: bool) -> bool:
    """Like or unlike a released chapter. False when it is not released."""
    if not chapter.is_published:
        return False
    if liked:
        ChapterLike.objects.get_or_create(reader=reader, chapter=chapter)
    else:
        ChapterLike.objects.filter(reader=reader, chapter=chapter).delete()
    return True


def set_chapter_favourite(reader, chapter, *, favourited: bool) -> bool:
    """Favourite or unfavourite a released chapter. False when it is not released."""
    if not chapter.is_published:
        return False
    if favourited:
        ChapterFavourite.objects.get_or_create(reader=reader, chapter=chapter)
    else:
        ChapterFavourite.objects.filter(reader=reader, chapter=chapter).delete()
    return True


def released_chapter_counts(story) -> list[dict]:
    """Counts for released chapters only. Drafts are omitted, not returned as zero."""
    rows = (
        Chapter.objects.filter(story=story, is_published=True)
        .annotate(
            read_count=Count("reads", distinct=True),
            like_count=Count("likes", distinct=True),
            favourite_count=Count("favourites", distinct=True),
        )
        .order_by("number")
        .values("number", "read_count", "like_count", "favourite_count")
    )
    return [
        {
            "number": row["number"],
            "reads": row["read_count"],
            "likes": row["like_count"],
            "favourites": row["favourite_count"],
        }
        for row in rows
    ]
