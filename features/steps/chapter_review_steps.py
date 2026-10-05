"""Behave steps for one-chapter review. The OpenAI client is stubbed."""

import json
import re
from html.parser import HTMLParser

from behave import given, then, when
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from django.urls import NoReverseMatch, reverse

import editor.assist as assist
from editor import urls as editor_urls
from editor.openai_provider import Completion, OpenAIError
from stories.models import Chapter, Story

_WORD = re.compile(r"[a-z0-9]+")
_VOID = {
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
_ALL_CLEAR = ("no gaps", "all clear", "all-clear", "no issues", "looks good")
_DID_NOT_RUN = ("did not run", "nothing proved")
_GAP_NOTE = ("nothing was applied", "nothing proved", "did not run")
_WRITE_WORDS = ("insert", "replace", "accept", "apply", "rewrite", "generate")
_ROUTE_WORDS = _WRITE_WORDS + ("confirm",)
_ROUTE_SUFFIXES = (
    "replace",
    "insert",
    "accept",
    "apply",
    "generate",
    "rewrite",
    "confirm",
)


class _El:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.parts = []

    def text(self):
        chunks = []
        for part in self.parts:
            if isinstance(part, str):
                chunks.append(part)
            else:
                chunks.append(part.text())
        return "".join(chunks)

    def visible(self):
        if self.tag in {"script", "style"}:
            return ""
        chunks = []
        for part in self.parts:
            if isinstance(part, str):
                chunks.append(part)
            else:
                chunks.append(part.visible())
        return "".join(chunks)


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = []
        self.roots = []
        self.by_id = {}

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1] if self.stack else None
        node = _El(tag, attrs, parent)
        if parent is None:
            self.roots.append(node)
        else:
            parent.parts.append(node)
        self.nodes.append(node)
        element_id = node.attrs.get("id")
        if element_id:
            self.by_id[element_id] = node
        if tag not in _VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].parts.append(data)


class StubProvider:
    """Stand-in for editor.assist.get_provider. It never opens a socket."""

    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _completion(text):
    return Completion(
        text=text,
        model="gpt-test-model",
        input_tokens=3,
        output_tokens=5,
        usage_known=True,
    )


def _assign_settings(context, **kwargs):
    originals = context._setting_originals
    for key, value in kwargs.items():
        if key not in originals:
            originals[key] = getattr(settings, key)
        setattr(settings, key, value)


def _install_stub(context, result):
    context.stub = StubProvider(result)
    if getattr(context, "_provider_module", None) is None:
        context._provider_module = assist
        context._original_get_provider = assist.get_provider
    assist.get_provider = lambda: context.stub


def _parse(html):
    parser = _Page()
    parser.feed(html)
    return parser


def _walk(node):
    yield node
    for part in node.parts:
        if not isinstance(part, str):
            yield from _walk(part)


def _words(value):
    return _WORD.findall((value or "").casefold())


def _accessible_name(node, by_id):
    label = node.attrs.get("aria-label")
    if label:
        return " ".join(label.split())
    labelledby = node.attrs.get("aria-labelledby")
    if labelledby:
        names = []
        for element_id in labelledby.split():
            target = by_id.get(element_id)
            if target is not None:
                names.append(target.visible())
        if names:
            return " ".join(" ".join(names).split())
    if node.tag == "input":
        return " ".join((node.attrs.get("value") or "").split())
    return " ".join(node.visible().split())


def _hidden(node):
    if node.attrs.get("type") == "hidden":
        return True
    if "hidden" in node.attrs:
        return True
    return node.attrs.get("aria-hidden") == "true"


def _keyboard(node):
    if _hidden(node) or node.attrs.get("tabindex") == "-1":
        return False
    if node.attrs.get("disabled") is not None:
        return False
    if node.tag == "button":
        return True
    if node.tag == "a" and node.attrs.get("href"):
        return True
    return node.tag == "input" and node.attrs.get("type") in {"button", "submit"}


def _controls(nodes, by_id, word):
    found = []
    for node in nodes:
        if _keyboard(node) and word in _words(_accessible_name(node, by_id)):
            found.append(node)
    return found


def _visible_page(parser):
    return "".join(root.visible() for root in parser.roots)


def _panel_node(parser):
    for node in parser.nodes:
        if node.attrs.get("id") == "review-panel":
            return node
        role = node.attrs.get("role")
        if role not in {"region", "complementary"}:
            continue
        name = _words(_accessible_name(node, parser.by_id))
        if "review" in name:
            return node
    return None


def _manuscript(parser):
    node = parser.by_id.get("manuscript")
    if node is None:
        raise AssertionError("The chapter page has no manuscript.")
    return node.text()


def _review_path(context):
    try:
        return reverse(
            "editor:review",
            kwargs={"slug": context.story.slug, "number": context.chapter.number},
        )
    except NoReverseMatch:
        return None


def _require_surface(context):
    parser = _parse(context.page)
    gaps = []
    if _review_path(context) is None:
        gaps.append(
            "Issue #6 (review API): editor:review is not registered, "
            "so a chapter review cannot be requested."
        )
    if not _controls(parser.nodes, parser.by_id, "review"):
        gaps.append(
            "Issue #5 (review panel): the chapter page has no keyboard Review control."
        )
    if gaps:
        lines = "\n".join(f"- {gap}" for gap in gaps)
        raise AssertionError(
            "Fail closed: the chapter review surface is not on main, "
            "so this scenario is not skipped and does not pass.\n" + lines
        )


def _request_url(node):
    for key in ("formaction", "hx-post", "data-url"):
        value = (node.attrs.get(key) or "").strip()
        if value and not value.startswith("#"):
            return value
    parent = node.parent
    while parent is not None:
        if parent.tag == "form":
            if parent.attrs.get("id") == "chapter-form":
                return None
            action = (parent.attrs.get("action") or "").strip()
            if action and "autosave" not in action:
                return action
            return None
        parent = parent.parent
    return None


def _uses_form(node):
    if node.attrs.get("formaction"):
        return True
    parent = node.parent
    while parent is not None:
        if parent.tag == "form" and parent.attrs.get("id") != "chapter-form":
            return True
        parent = parent.parent
    return False


def _csrf(parser):
    for node in parser.nodes:
        if node.tag == "input" and node.attrs.get("name") == "csrfmiddlewaretoken":
            return node.attrs.get("value") or ""
    return ""


def _activate(context, control, parser):
    url = _request_url(control)
    if not url:
        raise AssertionError(
            "The Review control does not declare a request, "
            "so the keyboard cannot run the review."
        )
    if url.rstrip("/").endswith("/autosave"):
        raise AssertionError(
            "The Review control submits the chapter form. "
            "Review must not write the manuscript."
        )
    if _uses_form(control):
        return context.client.post(
            url,
            data={"csrfmiddlewaretoken": _csrf(parser)},
            follow=True,
        )
    return context.client.post(
        url,
        data=b"",
        content_type="application/json",
        follow=True,
    )


def _open_editor(context):
    url = reverse(
        "editor:edit",
        kwargs={"slug": context.story.slug, "number": context.chapter.number},
    )
    context.response = context.client.get(url)
    assert context.response.status_code == 200, context.response.status_code
    context.page = context.response.content.decode()
    return context.page


def _set_body(context, body):
    context.chapter.content = body
    context.chapter.save(update_fields=["content", "updated_at"])
    context.original_body = body


def _assert_body(context, body):
    context.chapter.refresh_from_db()
    stored = context.chapter.content.encode("utf-8")
    expected = body.encode("utf-8")
    assert (
        stored == expected
    ), f"Stored chapter body is {stored!r}, expected {expected!r}."
    assert context.chapter.title == context.chapter_title


def _require_panel(context):
    parser = _parse(context.page)
    node = _panel_node(parser)
    if node is None:
        raise AssertionError(
            "Issue #5 (review panel): the chapter page has no review panel "
            "after the review, so the result is not shown."
        )
    return parser, node


def _focus_target(node):
    for key in ("href", "data-focus", "data-target"):
        value = node.attrs.get(key) or ""
        if "manuscript" in value:
            return value
    return ""


def _finding(panel, parser, question):
    best = None
    for node in _walk(panel):
        if question not in node.visible():
            continue
        nodes = list(_walk(node))
        if _controls(nodes, parser.by_id, "jump") or _controls(
            nodes, parser.by_id, "dismiss"
        ):
            best = node
    return best or panel


def _no_all_clear(text):
    lowered = text.casefold()
    for phrase in _ALL_CLEAR:
        assert phrase not in lowered, f"The page says {phrase!r} for a review."


@given('I am writing chapter "{title}" of "{story_title}" as "{username}"')
def step_writing(context, title, story_title, username):
    user = User.objects.create_user(username=username, password="securepass123")
    story = Story.objects.create(
        author=user,
        title=story_title,
        synopsis="A quiet valley.",
    )
    chapter = Chapter.objects.create(
        story=story,
        number=1,
        title=title,
        content="",
        is_published=False,
    )
    context.client = Client()
    assert context.client.login(username=username, password="securepass123")
    context.user = user
    context.story = story
    context.chapter = chapter
    context.chapter_title = title
    context.original_body = ""


@given('that chapter body is "{body}"')
def step_body(context, body):
    _set_body(context, body)


@given("that chapter body is empty")
def step_body_empty(context):
    _set_body(context, "")


@given("the AI assist flag is on")
def step_flag_on(context):
    _assign_settings(
        context,
        AI_ASSIST_ENABLED=True,
        WORLDS_ENVIRONMENT="local",
        OPENAI_API_KEY="",
        OPENAI_MODEL="gpt-test-model",
    )


@given("the AI assist flag is off")
def step_flag_off(context):
    _assign_settings(
        context,
        AI_ASSIST_ENABLED=False,
        WORLDS_ENVIRONMENT="local",
        OPENAI_API_KEY="",
        OPENAI_MODEL="gpt-test-model",
    )


@given('the OpenAI client is stubbed to return the rewrite "{rewrite}"')
def step_stub_rewrite(context, rewrite):
    context.rewrite = rewrite
    _install_stub(context, _completion(rewrite))


@given("the OpenAI client is stubbed to be unavailable")
def step_stub_down(context):
    _install_stub(context, OpenAIError("unavailable"))


@given(
    'the OpenAI client is stubbed to return the question "{question}" '
    'anchored at "{anchor}"'
)
def step_stub_question(context, question, anchor):
    assert anchor in context.chapter.content
    context.question = question
    context.anchor = anchor
    payload = json.dumps({"findings": [{"anchor": anchor, "question": question}]})
    _install_stub(context, _completion(payload))


@given('the OpenAI client is stubbed to invent "{marker}"')
def step_stub_invented(context, marker):
    context.invented = marker
    payload = json.dumps(
        {"findings": [{"anchor": marker, "question": f"Why does {marker} happen?"}]}
    )
    _install_stub(context, _completion(payload))


@when("I open that chapter in the editor")
def step_open(context):
    _open_editor(context)


@when('I edit the chapter body to "{body}" and autosave')
def step_autosave(context, body):
    url = reverse(
        "editor:autosave",
        kwargs={"slug": context.story.slug, "number": context.chapter.number},
    )
    context.response = context.client.post(
        url,
        data=json.dumps({"title": context.chapter.title, "content": body}),
        content_type="application/json",
    )
    context.edited_body = body


@when("I run the review from the keyboard")
def step_run_review(context):
    if not getattr(context, "page", None):
        _open_editor(context)
    _require_surface(context)
    parser = _parse(context.page)
    controls = _controls(parser.nodes, parser.by_id, "review")
    _activate(context, controls[0], parser)
    _open_editor(context)


@when("I jump to that finding from the keyboard")
def step_jump(context):
    parser, panel = _require_panel(context)
    container = _finding(panel, parser, context.question)
    controls = _controls(list(_walk(container)), parser.by_id, "jump")
    if not controls:
        raise AssertionError(
            "Issue #5 (review panel): the finding has no keyboard Jump control."
        )
    target = _focus_target(controls[0])
    if "manuscript" not in target:
        raise AssertionError(
            "Issue #5 (review panel): Jump does not move focus to the manuscript."
        )
    context.jump_target = target
    context.chapter.refresh_from_db()
    assert context.chapter.content == context.original_body


@when("I dismiss that finding from the keyboard")
def step_dismiss(context):
    parser, panel = _require_panel(context)
    container = _finding(panel, parser, context.question)
    controls = _controls(list(_walk(container)), parser.by_id, "dismiss")
    if not controls:
        raise AssertionError(
            "Issue #5 (review panel): the finding has no keyboard Dismiss control."
        )
    control = controls[0]
    url = _request_url(control)
    if not url:
        raise AssertionError(
            "Dismiss is not keyboard-activatable: it does not declare a POST URL."
        )
    if _uses_form(control):
        context.client.post(url, data={"csrfmiddlewaretoken": _csrf(parser)})
    else:
        context.client.post(url, data=b"", content_type="application/json")
    _open_editor(context)


@then("the chapter page has no review control")
def step_no_review_control(context):
    parser = _parse(context.page)
    controls = _controls(parser.nodes, parser.by_id, "review")
    assert controls == [], "The chapter page has a Review control while AI is off."


@then("the chapter page does not say there are no gaps")
def step_not_all_clear(context):
    _no_all_clear(_visible_page(_parse(context.page)))


@then('the stored chapter body is exactly "{body}"')
@then('the stored chapter body is byte-for-byte "{body}"')
def step_body_is(context, body):
    _assert_body(context, body)


@then("the stored chapter body is empty")
def step_stored_empty(context):
    _assert_body(context, "")


@then("the OpenAI client was not called")
def step_client_not_called(context):
    assert context.stub.calls == [], "The OpenAI client was called."
    assert context.live_openai_calls == [], "The live OpenAI API was called."


@then("the live OpenAI API was not called")
def step_live_not_called(context):
    assert context.live_openai_calls == [], "The live OpenAI API was called."


@then('the autosave response is "{label}"')
def step_autosave_label(context, label):
    assert context.response.status_code == 200, context.response.status_code
    assert context.response.content.decode() == label


@then("the chapter page has no insert, replace, or accept control")
def step_no_write_controls(context):
    parser = _parse(context.page)
    visible = _visible_page(parser).casefold()
    assert "suggested paragraph" not in visible
    for word in _WRITE_WORDS:
        found = _controls(parser.nodes, parser.by_id, word)
        assert found == [], f"The chapter page has a {word} control."


@then("there is no route that writes model text into the chapter")
def step_no_write_route(context):
    rewrite = context.rewrite
    for pattern in editor_urls.urlpatterns:
        name = pattern.name or ""
        for word in _ROUTE_WORDS:
            assert word not in name, name
    payload = json.dumps(
        {
            "replacement": rewrite,
            "content": rewrite,
            "confirmation": f"Replace the chapter with: {rewrite}",
        }
    )
    for suffix in _ROUTE_SUFFIXES:
        response = context.client.post(
            f"/editor/{context.story.slug}/{context.chapter.number}/{suffix}/",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 404, suffix
    assist_url = reverse(
        "editor:assist",
        kwargs={"slug": context.story.slug, "number": context.chapter.number},
    )
    context.client.post(
        assist_url,
        data=payload,
        content_type="application/json",
    )
    review_url = _review_path(context)
    if review_url is not None:
        context.client.post(
            review_url,
            data=payload,
            content_type="application/json",
        )
    context.chapter.refresh_from_db()
    assert context.chapter.content == context.original_body
    assert rewrite not in context.chapter.content


@then('the review panel shows "{question}"')
def step_panel_shows(context, question):
    parser, panel = _require_panel(context)
    assert question in panel.visible()
    assert question not in _manuscript(parser)


@then('the review panel does not show "{question}"')
def step_panel_hides(context, question):
    _parser, panel = _require_panel(context)
    assert question not in panel.visible()


@then('the manuscript focus is the place "{anchor}"')
def step_focus_place(context, anchor):
    assert "manuscript" in context.jump_target
    parser = _parse(context.page)
    assert anchor in _manuscript(parser)
    context.chapter.refresh_from_db()
    assert anchor in context.chapter.content


@then("the chapter page says the review did not run")
def step_did_not_run(context):
    visible = _visible_page(_parse(context.page))
    lowered = visible.casefold()
    assert any(
        phrase in lowered for phrase in _DID_NOT_RUN
    ), "The chapter page does not say the review did not run."


@then('the rewrite "{rewrite}" is not in the chapter or the review panel')
def step_rewrite_dropped(context, rewrite):
    context.chapter.refresh_from_db()
    assert rewrite not in context.chapter.content
    assert rewrite not in context.page
    _parser, panel = _require_panel(context)
    assert rewrite not in panel.visible()
    lowered = _visible_page(_parser).casefold()
    assert any(phrase in lowered for phrase in _GAP_NOTE), (
        "The rewrite was dropped, and the page does not say the review "
        "failed to produce questions."
    )


@then("the chapter page says there is nothing to check")
def step_nothing_to_check(context):
    visible = _visible_page(_parse(context.page)).casefold()
    assert "nothing to check" in visible
    _no_all_clear(visible)


@then('the chapter shows no invented finding "{marker}"')
def step_no_invented(context, marker):
    context.chapter.refresh_from_db()
    assert marker not in context.chapter.content
    assert marker not in context.page
    parser = _parse(context.page)
    assert marker not in _manuscript(parser)
