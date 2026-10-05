"""Behave steps for one-chapter review. The OpenAI client is stubbed."""

import json
import re
from html.parser import HTMLParser

from behave import given, then, when
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.exceptions import FieldDoesNotExist
from django.test import Client
from django.test.testcases import LiveServerThread
from django.urls import NoReverseMatch, reverse
from playwright.sync_api import sync_playwright

import editor.assist as assist
from editor import urls as editor_urls
from editor.models import AICall, ReviewFinding
from editor.openai_provider import Completion, OpenAIError
from stories.models import Chapter, Story

try:
    from editor import anchors as review_anchors
except ImportError:
    review_anchors = None

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
_NOTHING_PROVED = "Nothing proved. The chapter text is unchanged."
_REWRITE_GAP = "The model returned replacement prose. Nothing was applied."
_INTEGER_TYPES = {
    "IntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "BigIntegerField",
    "SmallIntegerField",
}
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
_ANCHOR_NOT_ON_MAIN = (
    "Fail closed: PR #28 is not on main yet. Each finding returns "
    "question, status, quote (120 characters max), start_offset, and "
    "anchor_status, which is one of ok, changed, or none. "
    "start_offset counts UTF-16 code units, the same way the browser "
    "caret does, and it is sent only when anchor_status is ok. "
    "This scenario is not skipped."
)
_ANCHOR_STATUSES = {"ok", "changed", "none"}
_CHANGED_COPY = "This passage has changed"
_NONE_COPY = "Can't find this passage in the chapter"
_FOLD_LINES = 80
_CARET_SCRIPT = """
() => {
  const el = document.getElementById("manuscript");
  if (!el) {
    return null;
  }
  const style = getComputedStyle(el);
  const lineHeight = parseFloat(style.lineHeight);
  const before = el.value.slice(0, el.selectionStart);
  const line = before.split("\\n").length - 1;
  const caretTop = line * lineHeight;
  const viewTop = el.scrollTop;
  const viewBottom = viewTop + el.clientHeight;
  const active = document.activeElement;
  return {
    selectionStart: el.selectionStart,
    selectionEnd: el.selectionEnd,
    activeId: active ? active.id : "",
    value: el.value,
    lineHeight,
    inView: Number.isFinite(lineHeight)
      && caretTop >= viewTop - 2
      && caretTop + lineHeight <= viewBottom + 2,
  };
}
"""


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
            "Fail closed: this scenario is not skipped and does not pass.\n" + lines
        )


def _named_field(name):
    try:
        return ReviewFinding._meta.get_field(name)
    except FieldDoesNotExist:
        return None


def _anchor_contract_on_main():
    quote = _named_field("quote")
    offset = _named_field("start_offset")
    if (
        quote is None
        or quote.get_internal_type() != "CharField"
        or quote.max_length != 120
    ):
        return False
    if offset is None or offset.get_internal_type() not in _INTEGER_TYPES:
        return False
    if review_anchors is None or not hasattr(review_anchors, "present_finding"):
        return False
    try:
        reverse("editor:findings", kwargs={"slug": "probe", "number": 1})
    except NoReverseMatch:
        return False
    row = ReviewFinding(
        id=1,
        question="Does it stay?",
        status=ReviewFinding.Status.OPEN,
        quote="The river",
        start_offset=0,
    )
    presented = review_anchors.present_finding(row, "The river stays.")
    if not isinstance(presented, dict):
        return False
    return {"question", "status", "quote", "anchor_status"} <= set(presented)


def _require_anchor_contract():
    if not _anchor_contract_on_main():
        raise AssertionError(_ANCHOR_NOT_ON_MAIN)


def _utf16_len(text):
    """UTF-16 code units, the index a browser caret uses."""
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def _quote_offset(chapter, quote):
    index = chapter.find(quote)
    if index < 0:
        raise AssertionError(
            "The quote is not in the chapter, so there is no browser offset."
        )
    return _utf16_len(chapter[:index]), index


def _any_named(nodes, by_id, word):
    """Controls with this name, including disabled and hidden ones."""
    found = []
    for node in nodes:
        role = node.attrs.get("role")
        if node.tag not in {"button", "a", "input"} and role not in {"button", "link"}:
            continue
        if word in _words(_accessible_name(node, by_id)):
            found.append(node)
    return found


def _read_finding(context):
    url = reverse(
        "editor:findings",
        kwargs={"slug": context.story.slug, "number": context.chapter.number},
    )
    response = context.client.get(url)
    assert response.status_code == 200, response.status_code
    payload = json.loads(response.content.decode())
    rows = [
        row
        for row in payload.get("findings", [])
        if row.get("question") == context.question
    ]
    assert len(rows) == 1, payload
    return rows[0]


def _close_browser(context):
    browser = getattr(context, "_browser", None)
    playwright = getattr(context, "_playwright", None)
    server = getattr(context, "_live_server", None)
    context._browser = None
    context._playwright = None
    context._live_server = None
    context._page = None
    if browser is not None:
        browser.close()
    if playwright is not None:
        playwright.stop()
    if server is not None:
        server.terminate()


def _launch_browser(playwright):
    args = ["--no-sandbox", "--disable-dev-shm-usage"]
    errors = []
    attempts = (
        {"channel": "chrome", "headless": True, "args": args},
        {"headless": True, "args": args},
    )
    for kwargs in attempts:
        try:
            return playwright.chromium.launch(**kwargs)
        except Exception as exc:
            errors.append(str(exc))
    raise AssertionError(
        "The caret must be read in a browser. Chrome did not start:\n"
        + "\n".join(errors)
    )


def _live_server(context):
    server = getattr(context, "_live_server", None)
    if server is not None:
        return f"http://{server.host}:{server.port}"
    thread = LiveServerThread("localhost", StaticFilesHandler, port=0)
    thread.daemon = True
    thread.start()
    thread.is_ready.wait(timeout=15)
    if thread.error:
        raise thread.error
    context._live_server = thread
    context.close_browser = lambda: _close_browser(context)
    return f"http://{thread.host}:{thread.port}"


def _browser_page(context):
    if getattr(context, "_page", None) is not None:
        return context._page
    live = _live_server(context)
    playwright = sync_playwright().start()
    browser = _launch_browser(playwright)
    context._playwright = playwright
    context._browser = browser
    context.close_browser = lambda: _close_browser(context)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.set_default_timeout(8000)
    cookie = context.client.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie is None:
        raise AssertionError(
            "The writer is not signed in, so the browser cannot open the chapter."
        )
    page.context.add_cookies(
        [
            {
                "name": settings.SESSION_COOKIE_NAME,
                "value": cookie.value,
                "url": live,
            }
        ]
    )
    url = live + reverse(
        "editor:edit",
        kwargs={"slug": context.story.slug, "number": context.chapter.number},
    )
    page.goto(url)
    context._page = page
    return page


def _press_jump(page):
    panel = page.locator("#review-panel")
    if panel.count() == 0:
        panel = page.get_by_role("region", name=re.compile(r"review", re.I))
    if panel.count() == 0:
        panel = page.get_by_role("complementary", name=re.compile(r"review", re.I))
    if panel.count() == 0:
        raise AssertionError(
            "Issue #5 (review panel): the chapter page has no review panel "
            "after the review, so Jump cannot move the caret."
        )
    name = re.compile(r"\bjump\b", re.I)
    button = panel.get_by_role("button", name=name)
    link = panel.get_by_role("link", name=name)
    target = button if button.count() else link
    if target.count() == 0:
        raise AssertionError(
            "Issue #5 (review panel): the finding has no keyboard Jump control."
        )
    target.first.focus()
    page.keyboard.press("Enter")


def _measure_caret(page):
    measured = page.evaluate(_CARET_SCRIPT.strip())
    if not measured:
        raise AssertionError(
            "The chapter page has no manuscript to place the caret in."
        )
    if not measured["lineHeight"]:
        raise AssertionError("The browser did not report a caret line height.")
    return measured


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


def _payload(context):
    if context.review_payload is None:
        raise AssertionError("The review response was not JSON.")
    return context.review_payload


@when("I request a review of that chapter")
def step_request_review(context):
    url = _review_path(context)
    if url is None:
        raise AssertionError(
            "Fail closed: Issue #6 (review API): editor:review is not registered, "
            "so this scenario is not skipped and does not pass."
        )
    context.response = context.client.post(
        url,
        data=b"",
        content_type="application/json",
    )
    try:
        context.review_payload = json.loads(context.response.content.decode())
    except json.JSONDecodeError:
        context.review_payload = None


@then('the review records one open finding "{question}"')
def step_one_open_finding(context, question):
    assert context.response.status_code == 200, context.response.status_code
    payload = _payload(context)
    assert payload["status"] == "ok"
    findings = payload["findings"]
    assert len(findings) == 1
    row = findings[0]
    assert row["question"] == question
    assert row["status"] == "open"
    assert row["anchor"] == context.anchor
    stored = ReviewFinding.objects.get(pk=row["id"])
    assert stored.status == ReviewFinding.Status.OPEN
    assert stored.question == question
    assert stored.anchor == context.anchor
    assert stored.kind == ReviewFinding.Kind.QUESTION
    assert stored.chapter_id == context.chapter.id
    assert ReviewFinding.objects.count() == 1
    context.finding_id = stored.id
    context.finding_snapshot = {
        "anchor": stored.anchor,
        "question": stored.question,
        "model": stored.model,
        "kind": stored.kind,
        "chapter_id": stored.chapter_id,
        "asked_by_id": stored.asked_by_id,
    }


@when("I dismiss that finding through the review API")
def step_dismiss_api(context):
    url = reverse(
        "editor:dismiss",
        kwargs={
            "slug": context.story.slug,
            "number": context.chapter.number,
            "finding_id": context.finding_id,
        },
    )
    context.response = context.client.post(
        url,
        data=b"",
        content_type="application/json",
    )


@then("that finding is dismissed without rewriting the chapter")
def step_dismissed_only(context):
    assert context.response.status_code == 200, context.response.status_code
    body = json.loads(context.response.content.decode())
    assert body["status"] == "dismissed"
    assert body["id"] == context.finding_id
    stored = ReviewFinding.objects.get(pk=context.finding_id)
    assert stored.status == ReviewFinding.Status.DISMISSED
    snap = context.finding_snapshot
    assert stored.anchor == snap["anchor"]
    assert stored.question == snap["question"]
    assert stored.model == snap["model"]
    assert stored.kind == snap["kind"]
    assert stored.chapter_id == snap["chapter_id"]
    assert stored.asked_by_id == snap["asked_by_id"]
    context.chapter.refresh_from_db()
    assert context.chapter.content == context.original_body


@then("the review is recorded as not run and not as zero findings")
def step_not_run(context):
    payload = _payload(context)
    raw = context.response.content.decode()
    lowered = raw.casefold()
    assert payload["status"] == "gap"
    assert payload["message"] == _NOTHING_PROVED
    assert payload.get("findings") != []
    assert "findings" not in payload
    assert '"findings": []' not in raw
    assert '"findings":[]' not in raw
    for phrase in _ALL_CLEAR:
        assert phrase not in lowered
    assert ReviewFinding.objects.count() == 0
    call = AICall.objects.get()
    assert call.outcome == AICall.Outcome.PROVIDER_ERROR
    assert call.chapter_id == context.chapter.id
    assert call.sent_to_provider is True


@then('the rewrite "{rewrite}" is stored only as a gap note')
def step_rewrite_gap(context, rewrite):
    assert context.response.status_code == 200, context.response.status_code
    payload = _payload(context)
    raw = context.response.content.decode()
    assert payload["status"] == "gap"
    assert payload["message"] == _NOTHING_PROVED
    assert "no gaps" not in raw.casefold()
    assert rewrite not in raw
    note = payload["gap_note"]
    assert note["status"] == "open"
    assert note["question"] == _REWRITE_GAP
    assert rewrite not in note["question"]
    assert rewrite not in (note.get("anchor") or "")
    stored = ReviewFinding.objects.get(pk=note["id"])
    assert stored.kind == ReviewFinding.Kind.GAP
    assert stored.status == ReviewFinding.Status.OPEN
    assert stored.question == _REWRITE_GAP
    assert rewrite not in stored.question
    assert rewrite not in stored.anchor
    assert ReviewFinding.objects.filter(kind=ReviewFinding.Kind.QUESTION).count() == 0
    context.chapter.refresh_from_db()
    assert context.chapter.content == context.original_body


@then('the review stores no invented finding "{marker}"')
def step_no_invented_record(context, marker):
    payload = _payload(context)
    raw = context.response.content.decode()
    assert marker not in raw
    assert "no gaps" not in raw.casefold()
    assert payload.get("status") != "ok"
    assert not payload.get("findings")
    for row in ReviewFinding.objects.all():
        assert row.kind != ReviewFinding.Kind.QUESTION
        assert marker not in row.question
        assert marker not in row.anchor
    context.chapter.refresh_from_db()
    assert marker not in context.chapter.content


@given("each finding returns quote, start_offset, and anchor_status")
def step_require_anchor_contract(context):
    _require_anchor_contract()


@given('that chapter places "{passage}" below the fold')
def step_below_fold(context, passage):
    # A textarea drops one leading newline. Start with a word so the
    # browser caret index matches the stored chapter.
    _set_body(context, ("line\n" * _FOLD_LINES) + passage)


@given(
    'the OpenAI client is stubbed to return the question "{question}" '
    'quoted as "{quote}"'
)
def step_stub_quoted(context, question, quote):
    context.question = question
    context.quote = quote
    payload = json.dumps({"findings": [{"quote": quote, "question": question}]})
    _install_stub(context, _completion(payload))


@then("each finding row has only the question, Jump, and Dismiss")
def step_row_shape(context):
    parser, panel = _require_panel(context)
    question_words = set(_words(context.question))
    rows = []
    for node in _walk(panel):
        contained = list(_walk(node))
        names = {
            word
            for control in _controls(contained, parser.by_id, "jump")
            for word in _words(_accessible_name(control, parser.by_id))
        }
        if "jump" not in names:
            continue
        dismisses = _controls(contained, parser.by_id, "dismiss")
        if dismisses:
            rows.append(node)
    if not rows:
        raise AssertionError(
            "Issue #5 (review panel): the panel has no finding row with "
            "a keyboard Jump and Dismiss."
        )
    row = rows[-1]
    controls = [
        node
        for node in _walk(row)
        if _keyboard(node) and _accessible_name(node, parser.by_id)
    ]
    labels = [_accessible_name(control, parser.by_id) for control in controls]
    for label in labels:
        for banned in ("insert", "replace", "accept", "suggested"):
            assert banned not in _words(label), label
    visible_words = _words(row.visible())
    allowed = question_words | {"jump", "dismiss"}
    extra = [word for word in visible_words if word not in allowed]
    assert extra == [], f"The finding row has extra wording: {extra}"


@when("I jump to that finding from the keyboard in the browser")
def step_browser_jump(context):
    _require_anchor_contract()
    page = _browser_page(context)
    _press_jump(page)
    context.browser_caret = _measure_caret(page)


@then('that finding\'s anchor_status is "{status}"')
def step_anchor_status(context, status):
    _require_anchor_contract()
    if status not in _ANCHOR_STATUSES:
        raise AssertionError(f"anchor_status {status!r} is not ok, changed, or none.")
    _open_editor(context)
    row = _read_finding(context)
    actual = row.get("anchor_status")
    assert actual == status, f"anchor_status is {actual!r}, expected {status!r}."
    assert row.get("question") == context.question
    assert row.get("status") == "open"
    quote = row.get("quote")
    if quote is not None:
        assert len(quote) <= 120, quote
    if status == "ok":
        assert isinstance(row.get("start_offset"), int), row
    elif status == "changed":
        assert (
            "start_offset" not in row
        ), "start_offset is sent only when anchor_status is ok."
    elif status == "none":
        assert (
            "start_offset" not in row
        ), "start_offset is sent only when anchor_status is ok."
    else:
        raise AssertionError(f"anchor_status {status!r} is not ok, changed, or none.")
    context.finding_payload = row


@then("the browser caret is at that finding's start offset")
def step_browser_caret(context):
    context.chapter.refresh_from_db()
    expected, _python_index = _quote_offset(context.chapter.content, context.quote)
    measured = context.browser_caret
    actual = measured["selectionStart"]
    assert actual == expected, (
        f"The browser caret is at {actual}, and the UTF-16 offset of the "
        f"quote is {expected}."
    )
    assert context.finding_payload["start_offset"] == expected, (
        "The browser caret is at the quote, and the finding's start_offset "
        f"is {context.finding_payload.get('start_offset')!r}."
    )
    assert measured["value"] == context.chapter.content


@then("the browser caret counts the emoji before the quote as two characters")
def step_emoji_caret(context):
    context.chapter.refresh_from_db()
    chapter = context.chapter.content
    expected, python_index = _quote_offset(chapter, context.quote)
    prefix = chapter[:python_index]
    extra = sum(1 for char in prefix if ord(char) > 0xFFFF)
    assert extra >= 1, "The chapter has no emoji before the quote."
    assert expected == python_index + extra
    actual = context.browser_caret["selectionStart"]
    assert actual == expected, (
        f"The browser caret is at {actual}. The emoji before the quote "
        f"counts as two, so the caret belongs at {expected}, not the "
        f"Python index {python_index}."
    )


@then("the manuscript caret is scrolled into view")
def step_scrolled(context):
    assert context.browser_caret["inView"], (
        "Jump does not scroll the caret into view. "
        f"The browser caret is at {context.browser_caret['selectionStart']}."
    )


@then("focus stays in the chapter")
def step_focus_stays(context):
    active = context.browser_caret["activeId"]
    assert (
        active == "manuscript"
    ), f"Focus is on {active!r} after Jump. It belongs in the chapter."


@then("the chapter text is unchanged")
def step_text_unchanged(context):
    assert context.browser_caret["value"] == context.original_body
    _assert_body(context, context.original_body)


@then('the finding row shows "{sentence}"')
def step_row_shows(context, sentence):
    _parser, panel = _require_panel(context)
    container = _finding(panel, _parser, context.question)
    visible = container.visible()
    assert sentence in visible, f"The finding row does not show {sentence!r}."
    if sentence == _CHANGED_COPY:
        assert _NONE_COPY not in visible
    elif sentence == _NONE_COPY:
        assert _CHANGED_COPY not in visible


@then("the finding row keeps the question and Dismiss and has no Jump control")
def step_no_jump(context):
    parser, panel = _require_panel(context)
    container = _finding(panel, parser, context.question)
    nodes = list(_walk(container))
    assert context.question in container.visible()
    dismisses = _controls(nodes, parser.by_id, "dismiss")
    if not dismisses:
        raise AssertionError(
            "Issue #5 (review panel): the finding row has no keyboard Dismiss control."
        )
    jumps = _any_named(nodes, parser.by_id, "jump")
    if jumps:
        raise AssertionError(
            "The finding row has a Jump control. "
            "A disabled Jump does not count as absent."
        )
