"""HTML sanitization for chapter content."""

import bleach

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "s",
    "h1",
    "h2",
    "h3",
    "blockquote",
    "ul",
    "ol",
    "li",
    "hr",
    "a",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}


def sanitize_html(html: str) -> str:
    """Sanitize rich-text HTML for safe display."""
    if not html:
        return ""
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def render_chapter_content(chapter) -> str:
    """Return display-ready chapter content."""
    from stories.models import ContentFormat

    if chapter.content_format == ContentFormat.HTML:
        return sanitize_html(chapter.content)
    return chapter.content
