"""Editor autosave and writer-chrome tests."""

import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.urls import reverse

from stories.models import Chapter
from tests.factories import ChapterFactory

PARAGRAPH = (
    "The river kept its course through the quiet valley, "
    "and the morning stayed with that one sentence."
)
REPLACEMENT = "This sentence must not replace the chapter when the save fails."
ROOT = Path(__file__).resolve().parents[1]


_VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}


class _Nodes(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        attr = {key: value for key, value in attrs}
        parent = self.stack[-1] if self.stack else None
        self.nodes.append({"tag": tag, "attrs": attr, "parent": parent})
        self.stack.append({"tag": tag, "attrs": attr})
        if tag in _VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break


def _edit_url(story, number=1):
    return reverse("editor:edit", kwargs={"slug": story.slug, "number": number})


def _autosave_url(story, number=1):
    return reverse("editor:autosave", kwargs={"slug": story.slug, "number": number})


def _parse(html):
    parser = _Nodes()
    parser.feed(html)
    return parser.nodes


def _by_id(nodes, element_id):
    matches = [node for node in nodes if node["attrs"].get("id") == element_id]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.django_db
class TestEditor:
    def test_autosave_updates_chapter(self, client_logged_in, story):
        chapter = ChapterFactory(
            story=story, number=1, title="Old", content="Old content"
        )
        url = _autosave_url(story)
        response = client_logged_in.post(
            url,
            data=json.dumps({"title": "New Title", "content": "New content here."}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.content.decode() == "Saved"
        chapter.refresh_from_db()
        assert chapter.title == "New Title"
        assert chapter.content == "New content here."

    def test_editor_requires_author(self, client, story, reader):
        ChapterFactory(story=story, number=1)
        client.login(username="reader1", password="testpass123")
        response = client.get(_edit_url(story))
        assert response.status_code == 404

    def test_open_chapter_is_the_manuscript_without_funding_chrome(
        self, client_logged_in, story
    ):
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        response = client_logged_in.get(_edit_url(story))
        assert response.status_code == 200
        html = response.content.decode()
        assert PARAGRAPH in html
        assert "Dawn" in html
        for banned in (
            "Discover",
            "Payments",
            "Fund the next generation",
            "Fund emerging authors",
            "Your library",
            "Start writing",
            "Sign out",
            "Subscribe",
        ):
            assert banned not in html
        assert reverse("stories:discover") not in html
        assert reverse("payments:history") not in html
        assert reverse("library:index") not in html
        assert "<nav" not in html
        assert "<footer" not in html
        assert "<aside" not in html
        assert "score" not in html.lower()
        nodes = _parse(html)
        manuscript = _by_id(nodes, "manuscript")
        assert manuscript["tag"] == "textarea"
        assert "editor-strip" not in (manuscript["parent"] or {}).get("attrs", {}).get(
            "class", ""
        )
        strip_children = [
            node["attrs"].get("id")
            for node in nodes
            if node["parent"]
            and "editor-strip" in node["parent"]["attrs"].get("class", "")
        ]
        assert strip_children == ["chapter-title", "save-status"]
        assert 'id="chapter-menu"' in html
        assert 'hx-trigger="flush"' in html

    def test_visible_status_matches_autosave_result(self, client_logged_in, story):
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        saved = client_logged_in.post(
            _autosave_url(story),
            data={"title": "Dawn", "content": PARAGRAPH + " The water was cold."},
        )
        assert saved.status_code == 200
        assert saved.content.decode() == "Saved"
        assert "The water was cold." not in saved.content.decode()

        chapter = Chapter.objects.get(story=story, number=1)
        failed = client_logged_in.post(
            _autosave_url(story),
            data=b"not-json",
            content_type="application/json",
        )
        assert failed.status_code >= 400
        assert failed.content.decode() == "Failed"
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH + " The water was cold."

    def test_failed_autosave_keeps_chapter_text(
        self, client_logged_in, story, monkeypatch
    ):
        chapter = ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)

        def explode(self, *args, **kwargs):
            raise RuntimeError("disk full")

        monkeypatch.setattr(Chapter, "save", explode)
        response = client_logged_in.post(
            _autosave_url(story),
            data=json.dumps({"title": "Gone", "content": REPLACEMENT}),
            content_type="application/json",
        )
        assert response.status_code >= 400
        assert response.content.decode() == "Failed"
        assert REPLACEMENT not in response.content.decode()
        chapter.refresh_from_db()
        assert chapter.title == "Dawn"
        assert chapter.content == PARAGRAPH

    def test_null_content_does_not_clear_chapter(self, client_logged_in, story):
        chapter = ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        response = client_logged_in.post(
            _autosave_url(story),
            data=json.dumps({"title": "Dawn", "content": None}),
            content_type="application/json",
        )
        assert response.status_code >= 400
        assert response.content.decode() == "Failed"
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH

    def test_keyboard_reaches_manuscript_status_and_book(self, client_logged_in, story):
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        html = client_logged_in.get(_edit_url(story)).content.decode()
        nodes = _parse(html)
        back = _by_id(nodes, "back-to-book")
        status = _by_id(nodes, "save-status")
        manuscript = _by_id(nodes, "manuscript")
        assert back["tag"] == "a"
        assert back["attrs"].get("href") == reverse(
            "stories:manage", kwargs={"slug": story.slug}
        )
        assert status["attrs"].get("tabindex") == "0"
        assert status["attrs"].get("role") == "status"
        assert manuscript["tag"] == "textarea"
        assert [node for node in nodes if node["tag"] == "button"] == []

    def test_page_has_no_review_control_and_no_model_call(
        self, client_logged_in, story
    ):
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        html = client_logged_in.get(_edit_url(story)).content.decode()
        lowered = html.lower()
        for banned in (
            "openai",
            "chatgpt",
            "gpt-",
            "anthropic",
            "ghostwrite",
            "findings",
            "generate",
            'role="dialog"',
            "review",
        ):
            assert banned not in lowered
        assert html.count("hx-post=") == 1
        assert _autosave_url(story) in html
        assert 'hx-swap="none"' in html
        script = (ROOT / "static" / "editor" / "autosave.js").read_text()
        for banned in (
            "fetch(",
            "XMLHttpRequest",
            "openai",
            "innerHTML",
            ".value =",
            "review",
        ):
            assert banned not in script.lower()

    def test_chapter_title_is_larger_than_the_prose_and_status_stays_small(self):
        css = (ROOT / "static" / "editor" / "editor.css").read_text()
        column = css.split(".editor-column", 1)[1].split("}", 1)[0]
        title = css.split(".editor-title", 1)[1].split("}", 1)[0]
        status = css.split(".editor-status", 1)[1].split("}", 1)[0]
        prose = float(re.search(r"font-size:\s*([0-9.]+)rem", column).group(1))
        title_size = float(re.search(r"font-size:\s*([0-9.]+)rem", title).group(1))
        status_size = float(re.search(r"font-size:\s*([0-9.]+)rem", status).group(1))
        assert title_size > prose
        assert status_size < prose

    def test_manuscript_column_css_wraps_a_normal_paragraph(self):
        css = (ROOT / "static" / "editor" / "editor.css").read_text()
        column = css.split(".editor-column", 1)[1].split("}", 1)[0]
        manuscript = css.split(".manuscript", 1)[1].split("}", 1)[0]
        assert "width: 100%" in column
        assert "max-width" in column
        assert "width: 100%" in manuscript
        assert "max-width: 100%" in manuscript
        assert "overflow-wrap" in manuscript
        assert "nowrap" not in manuscript

    def test_autosave_status_script_keeps_text_and_matches_result(self):
        result = subprocess.run(
            ["node", str(ROOT / "static" / "editor" / "autosave.test.js")],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
