"""Review panel on the chapter page. The provider is stubbed. No live OpenAI."""

import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.urls import reverse

from editor.models import AICall, ReviewFinding
from editor.review import PASSAGE_CHANGED, PASSAGE_MISSING
from tests.factories import ChapterFactory
from tests.test_chapter_review import (
    ANCHOR_ONE,
    PARAGRAPH,
    QUESTION_ONE,
    StubProvider,
    _autosave,
    _completion,
    _dismiss_url,
    _edit_url,
    _enable,
    _install,
    _json,
    _post,
    _snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
EMPTY_CHAPTER = "There's nothing to review yet."
DID_NOT_RUN = "The review did not run. Your chapter hasn't changed."
NO_QUESTIONS = "No questions this time. Your chapter hasn't changed."
INSERT_LABELS = ("insert", "rewrite", "generate", "apply", "replace", "accept")


class _Nodes(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        attr = {key: value if value is not None else "" for key, value in attrs}
        parent = self.stack[-1] if self.stack else None
        node = {"tag": tag, "attrs": attr, "parent": parent, "text": ""}
        self.nodes.append(node)
        self.stack.append(node)
        if tag in {"input", "link", "meta", "br", "hr", "img", "source"}:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]["text"] += data

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break


def _parse(html):
    parser = _Nodes()
    parser.feed(html)
    return parser.nodes


def _by_id(nodes, element_id):
    matches = [node for node in nodes if node["attrs"].get("id") == element_id]
    assert len(matches) == 1, element_id
    return matches[0]


def _inside_column(node):
    current = node
    while current:
        if "editor-column" in current["attrs"].get("class", "").split():
            return True
        current = current.get("parent")
    return False


def _button_labels(nodes):
    return [" ".join(node["text"].split()) for node in nodes if node["tag"] == "button"]


@pytest.mark.django_db
class TestReviewHiddenWhenFlagOff:
    def test_chapter_page_has_no_review_control_and_makes_no_model_call(
        self, client_logged_in, story, monkeypatch
    ):
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)

        def explode():
            raise AssertionError("OpenAI was called")

        monkeypatch.setattr("editor.assist.get_provider", explode)
        response = client_logged_in.get(_edit_url(story))
        html = response.content.decode()
        assert response.status_code == 200
        assert "review" not in html.lower()
        assert "static/editor/review.js" not in html
        assert EMPTY_CHAPTER not in html
        assert [node for node in _parse(html) if node["tag"] == "button"] == []
        assert AICall.objects.count() == 0


@pytest.mark.django_db
class TestReviewPanelWhenFlagOn:
    def test_review_opens_in_the_chapter_column_and_the_page_does_not_call(
        self, client_logged_in, story, settings, monkeypatch
    ):
        _enable(settings)
        ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)

        def explode():
            raise AssertionError("OpenAI was called")

        monkeypatch.setattr("editor.assist.get_provider", explode)
        response = client_logged_in.get(_edit_url(story))
        html = response.content.decode()
        nodes = _parse(html)
        assert response.status_code == 200
        button = _by_id(nodes, "review-chapter")
        assert button["tag"] == "button"
        assert button["attrs"].get("type") == "button"
        assert button["text"].strip() == "Review"
        assert _inside_column(button)
        panel = _by_id(nodes, "review-panel")
        assert panel["tag"] != "aside"
        assert panel["attrs"].get("role") != "dialog"
        assert "hidden" in panel["attrs"]
        assert not _inside_column(panel)
        assert "editor-layout" in panel["parent"]["attrs"].get("class", "")
        assert html.index('class="editor-column"') < html.index('id="review-panel"')
        manuscript = _by_id(nodes, "manuscript")
        assert _inside_column(manuscript)
        assert manuscript["parent"]["attrs"].get("id") == "chapter-form"
        assert panel["parent"]["attrs"].get("id") != "chapter-form"
        assert html.count('class="editor-column"') == 1
        assert 'id="chapter-menu"' in html
        labels = [
            node["text"].strip()
            for node in nodes
            if node["tag"] == "label" and node["attrs"].get("for") == "chapter-menu"
        ]
        assert labels == ["Chapters"]
        root = _by_id(nodes, "chapter-editor")
        assert root["attrs"].get("data-review-url") == reverse(
            "editor:review", kwargs={"slug": story.slug, "number": 1}
        )
        assert root["attrs"].get("data-empty-chapter") == EMPTY_CHAPTER
        assert root["attrs"].get("data-did-not-run") == DID_NOT_RUN
        assert root["attrs"].get("data-no-questions") == NO_QUESTIONS
        assert "data-nothing-proved" not in html
        assert "Nothing proved. The chapter text is unchanged." not in html
        assert root["attrs"].get("data-passage-changed") == PASSAGE_CHANGED
        assert root["attrs"].get("data-passage-missing") == PASSAGE_MISSING
        assert "static/editor/review.js" in html
        assert (
            reverse("editor:assist", kwargs={"slug": story.slug, "number": 1})
            not in html
        )
        lowered = html.lower()
        assert "generate" not in lowered
        assert "openai" not in lowered
        assert "gpt-" not in lowered
        assert "score" not in lowered
        assert "no gaps" not in lowered
        assert 'role="dialog"' not in html
        assert "<aside" not in html
        for label in _button_labels(nodes):
            assert label.lower() not in INSERT_LABELS
        assert "disabled" not in manuscript["attrs"]
        assert "readonly" not in manuscript["attrs"]
        form = _by_id(nodes, "chapter-form")
        assert form["attrs"].get("hx-swap") == "none"
        assert AICall.objects.count() == 0

    def test_panel_css_does_not_cover_the_manuscript(self):
        css = (ROOT / "static" / "editor" / "editor.css").read_text()
        panel = css.split(".review-panel", 1)[1].split("}", 1)[0]
        assert "position: static" in panel
        assert "fixed" not in panel
        assert "absolute" not in panel
        assert "z-index" not in panel
        title = css.split(".editor-title {", 1)[1].split("}", 1)[0]
        heading = css.split(".review-heading {", 1)[1].split("}", 1)[0]
        column = css.split(".editor-column {", 1)[1].split("}", 1)[0]
        layout = css.split(".editor-layout {", 1)[1].split("}", 1)[0]
        wide = css.split("@media (min-width: 1100px)", 1)[1]
        prose = float(re.search(r"font-size:\s*([0-9.]+)rem", column).group(1))
        title_size = float(re.search(r"font-size:\s*([0-9.]+)rem", title).group(1))
        heading_size = float(re.search(r"font-size:\s*([0-9.]+)rem", heading).group(1))
        assert title_size > prose
        assert heading_size < title_size
        assert "flex-direction: column" in layout
        assert "flex-direction: row" in wide
        assert "position: absolute" not in panel
        assert "position: fixed" not in panel

    def _row(self, client_logged_in, story, **fields):
        chapter = ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        finding = ReviewFinding.objects.create(
            chapter=chapter,
            asked_by=story.author,
            anchor="",
            question=QUESTION_ONE,
            status=ReviewFinding.Status.OPEN,
            model="gpt-review-model",
            kind=ReviewFinding.Kind.QUESTION,
            **fields,
        )
        html = client_logged_in.get(_edit_url(story)).content.decode()
        nodes = _parse(html)
        question = _by_id(nodes, f"review-question-{finding.id}")
        return html, nodes, question["parent"]

    def test_ok_anchor_shows_question_jump_and_dismiss(
        self, client_logged_in, story, settings
    ):
        _enable(settings)
        html, nodes, item = self._row(
            client_logged_in,
            story,
            quote=ANCHOR_ONE,
            start_offset=0,
        )
        assert item["attrs"].get("data-anchor-status") == "ok"
        assert item["attrs"].get("tabindex") == "-1"
        heading = _by_id(nodes, "review-heading")
        assert heading["attrs"].get("tabindex") == "-1"
        question = [
            node
            for node in nodes
            if node["attrs"].get("id") == item["attrs"].get("aria-labelledby")
        ][0]
        assert question["text"].strip() == QUESTION_ONE
        buttons = [
            node
            for node in nodes
            if node["tag"] == "button" and node.get("parent") is item
        ]
        labels = [" ".join(node["text"].split()) for node in buttons]
        assert labels == ["Jump", "Dismiss"]
        jump = buttons[0]
        assert jump["attrs"].get("type") == "button"
        assert "disabled" not in jump["attrs"]
        assert jump["attrs"].get("data-start-offset") == "0"
        assert "gpt-review-model" not in html
        assert "score" not in html.lower()
        notes = [
            node
            for node in nodes
            if node.get("parent") is item
            and "review-anchor-note" in node["attrs"].get("class", "")
        ]
        assert notes == []

    def test_changed_anchor_drops_jump_and_says_the_passage_changed(
        self, client_logged_in, story, settings
    ):
        _enable(settings)
        gone = "a sentence the writer never wrote"
        html, nodes, item = self._row(
            client_logged_in,
            story,
            quote=gone,
            start_offset=0,
        )
        assert item["attrs"].get("data-anchor-status") == "changed"
        notes = [
            node["text"].strip()
            for node in nodes
            if node.get("parent") is item and node["tag"] == "p"
        ]
        assert PASSAGE_CHANGED in notes
        assert PASSAGE_MISSING not in notes
        buttons = [
            " ".join(node["text"].split())
            for node in nodes
            if node["tag"] == "button" and node.get("parent") is item
        ]
        assert buttons == ["Dismiss"]
        assert gone not in html
        assert all(
            "disabled" not in node["attrs"] for node in nodes if node["tag"] == "button"
        )

    def test_missing_or_duplicate_anchor_drops_jump(
        self, client_logged_in, story, settings
    ):
        _enable(settings)
        html, nodes, item = self._row(
            client_logged_in,
            story,
            quote=None,
            start_offset=None,
        )
        assert item["attrs"].get("data-anchor-status") == "none"
        notes = [
            node["text"].strip()
            for node in nodes
            if node.get("parent") is item and node["tag"] == "p"
        ]
        assert PASSAGE_MISSING in notes
        assert PASSAGE_CHANGED not in notes
        buttons = [
            " ".join(node["text"].split())
            for node in nodes
            if node["tag"] == "button" and node.get("parent") is item
        ]
        assert buttons == ["Dismiss"]

        chapter = story.chapters.get(number=1)
        chapter.content = ANCHOR_ONE + " and then " + ANCHOR_ONE
        chapter.save(update_fields=["content", "updated_at"])
        finding = ReviewFinding.objects.get()
        finding.quote = ANCHOR_ONE
        finding.start_offset = 3
        finding.save(update_fields=["quote", "start_offset"])
        again = client_logged_in.get(_edit_url(story)).content.decode()
        again_nodes = _parse(again)
        row = [
            node
            for node in again_nodes
            if node["attrs"].get("data-finding-id") == str(finding.id)
        ][0]
        assert row["attrs"].get("data-anchor-status") == "none"
        again_notes = [
            node["text"].strip()
            for node in again_nodes
            if node.get("parent") is row and node["tag"] == "p"
        ]
        assert PASSAGE_MISSING in again_notes
        again_buttons = [
            " ".join(node["text"].split())
            for node in again_nodes
            if node["tag"] == "button" and node.get("parent") is row
        ]
        assert again_buttons == ["Dismiss"]
        assert "Jump" not in again_buttons


@pytest.mark.django_db
class TestEmptyChapter:
    @pytest.mark.parametrize("content", ["", "   ", "\n\n"])
    def test_empty_chapter_says_there_is_nothing_to_check(
        self, client_logged_in, story, settings, monkeypatch, content
    ):
        _enable(settings)
        chapter = ChapterFactory(story=story, number=1, title="Dawn", content=content)
        before = _snapshot(chapter)
        stub = _install(monkeypatch, StubProvider(_completion()))
        response = _post(client_logged_in, story)
        assert response.status_code == 200
        body = _json(response)
        assert body["state"] == "empty"
        assert body["status"] == "empty"
        assert body["message"] == EMPTY_CHAPTER
        assert "findings" not in body
        assert "gap_note" not in body
        assert "no gaps" not in response.content.decode().lower()
        assert stub.calls == []
        assert _snapshot(chapter) == before
        assert ReviewFinding.objects.count() == 0
        assert AICall.objects.count() == 0


@pytest.mark.django_db
class TestRunReviewDismissLeavesChapter:
    def test_run_review_see_finding_dismiss_it_and_chapter_body_is_unchanged(
        self, client_logged_in, story, settings, monkeypatch
    ):
        _enable(settings)
        chapter = ChapterFactory(story=story, number=1, title="Dawn", content=PARAGRAPH)
        before = _snapshot(chapter)
        stub = _install(monkeypatch, StubProvider(_completion()))

        opened = client_logged_in.get(_edit_url(story))
        assert QUESTION_ONE not in opened.content.decode()
        assert stub.calls == []

        reviewed = _post(client_logged_in, story)
        assert reviewed.status_code == 200
        body = _json(reviewed)
        assert body["state"] == "ran"
        assert body["status"] == "ok"
        assert body["findings"][0]["question"] == QUESTION_ONE
        assert body["findings"][0]["quote"] == ANCHOR_ONE
        assert body["findings"][0]["anchor_status"] == "ok"
        assert body["findings"][0]["start_offset"] == 0
        assert "no gaps" not in reviewed.content.decode().lower()
        assert stub.calls
        assert _snapshot(chapter) == before

        shown = client_logged_in.get(_edit_url(story))
        shown_html = shown.content.decode()
        assert QUESTION_ONE in shown_html
        assert ANCHOR_ONE in shown_html
        assert f">{PARAGRAPH}<" in shown_html or PARAGRAPH in shown_html

        finding = ReviewFinding.objects.get(question=QUESTION_ONE)
        dismissed = client_logged_in.post(_dismiss_url(story, finding.id))
        assert dismissed.status_code == 200
        assert _json(dismissed)["status"] == "dismissed"
        assert _snapshot(chapter) == before
        finding.refresh_from_db()
        assert finding.status == ReviewFinding.Status.DISMISSED

        after = client_logged_in.get(_edit_url(story)).content.decode()
        assert QUESTION_ONE not in after
        assert PARAGRAPH in after
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH

        saved = _autosave(client_logged_in, story, PARAGRAPH + " Still mine.")
        assert saved.status_code == 200
        assert saved.content.decode() == "Saved"
        chapter.refresh_from_db()
        assert chapter.content == PARAGRAPH + " Still mine."


def test_review_script_asks_and_does_not_write():
    result = subprocess.run(
        ["node", str(ROOT / "static" / "editor" / "review.test.js")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
