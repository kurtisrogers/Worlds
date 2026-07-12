"""Tests for content sanitization and HTML rendering."""

import pytest

from stories.content import render_chapter_content, sanitize_html
from stories.models import ContentFormat
from tests.factories import ChapterFactory


class TestContentSanitization:
    def test_sanitize_strips_script_tags(self):
        dirty = '<p>Hello</p><script>alert("xss")</script>'
        clean = sanitize_html(dirty)
        assert "script" not in clean
        assert "Hello" in clean

    def test_sanitize_allows_formatting(self):
        html = "<p><strong>Bold</strong> and <em>italic</em></p>"
        assert "<strong>" in sanitize_html(html)

    def test_render_plain_content(self, story):
        chapter = ChapterFactory(story=story, content="Plain text here.", content_format=ContentFormat.PLAIN)
        assert render_chapter_content(chapter) == "Plain text here."

    def test_render_html_content(self, story):
        chapter = ChapterFactory(
            story=story,
            content="<p>Rich <strong>text</strong></p>",
            content_format=ContentFormat.HTML,
        )
        rendered = render_chapter_content(chapter)
        assert "<strong>" in rendered
