const assert = require("assert");
const review = require("./review.js");

const NOTHING_YET = "There's nothing to review yet.";
const FAILED = "The review did not run. Your chapter hasn't changed.";
const NO_QUESTIONS = "No questions this time. Your chapter hasn't changed.";
const GAP = "Nothing proved. The chapter text is unchanged.";
const AUTHORSHIP = "This is assistance, not authorship.";
const REVIEWING = "Reviewing…";
const DISMISS_FAILED = "Couldn't dismiss. Try again.";
const QUESTION = "Does the river stay in the valley?";
const ANCHOR = "The river kept its course";
const CHAPTER = ANCHOR + " through the quiet valley.";

assert.strictEqual(review.isEmptyChapter(""), true);
assert.strictEqual(review.isEmptyChapter("   \n"), true);
assert.strictEqual(review.isEmptyChapter(CHAPTER), false);

assert.deepStrictEqual(review.prepareReview(""), { state: "empty" });
assert.deepStrictEqual(review.prepareReview("  "), { state: "empty" });
assert.deepStrictEqual(review.prepareReview(CHAPTER), { state: "request" });

const refused = review.interpretReview({
  state: "failed",
  status: "rejected",
  message: "A configured spend cap rejected this call.",
});
assert.strictEqual(refused.state, "failed");
assert.strictEqual(refused.message, FAILED);
assert.strictEqual(refused.replace, false);
assert.ok(!refused.message.includes(GAP));
assert.ok(!refused.message.toLowerCase().includes("no gaps"));

const ranEmpty = review.interpretReview({
  state: "ran",
  status: "gap",
  message: GAP,
  gap_note: { id: 4, question: GAP, status: "open" },
});
assert.strictEqual(ranEmpty.state, "ran");
assert.strictEqual(ranEmpty.message, NO_QUESTIONS);
assert.deepStrictEqual(ranEmpty.findings, []);
assert.strictEqual(ranEmpty.replace, true);
assert.ok(!ranEmpty.message.includes(GAP));
assert.ok(!ranEmpty.message.toLowerCase().includes("no gaps"));

const timedOut = review.interpretReview(null);
assert.strictEqual(timedOut.state, "failed");
assert.strictEqual(timedOut.message, FAILED);

const unknown = review.interpretReview({ status: "gap", message: GAP });
assert.strictEqual(unknown.state, "failed");
assert.strictEqual(unknown.message, FAILED);
assert.ok(!unknown.message.includes(GAP));

const empty = review.interpretReview({
  state: "empty",
  message: "There is nothing to check. Nothing proved.",
});
assert.strictEqual(empty.state, "empty");
assert.strictEqual(empty.message, NOTHING_YET);
assert.strictEqual(empty.replace, false);
assert.ok(!empty.message.includes("Nothing proved"));

const blankServerMessage = review.interpretReview({
  state: "ran",
  message: "",
  findings: [{ id: 7, question: QUESTION, anchor_status: "ok", start_offset: 0 }],
});
assert.strictEqual(blankServerMessage.message, "");

const found = review.interpretReview({
  state: "ran",
  message: AUTHORSHIP,
  findings: [
    {
      id: 3,
      question: QUESTION,
      status: "open",
      quote: ANCHOR,
      start_offset: 0,
      anchor_status: "ok",
    },
  ],
});
assert.strictEqual(found.state, "ran");
assert.strictEqual(found.message, "");
assert.strictEqual(found.findings[0].question, QUESTION);
assert.strictEqual(found.replace, true);

function manuscript(value) {
  return {
    value: value,
    selectionStart: 0,
    selectionEnd: 0,
    focused: false,
    focus() {
      this.focused = true;
    },
    setSelectionRange(start, end) {
      this.selectionStart = start;
      this.selectionEnd = end;
    },
  };
}

const jumped = manuscript(CHAPTER);
assert.strictEqual(review.jumpToOffset(jumped, 0), true);
assert.strictEqual(jumped.value, CHAPTER);
assert.strictEqual(jumped.focused, true);
assert.strictEqual(jumped.selectionStart, 0);
assert.strictEqual(jumped.selectionEnd, 0);

const emoji = "café 😀 " + ANCHOR;
const emojiField = manuscript(emoji);
assert.strictEqual("café 😀 ".length, 8);
assert.strictEqual(review.jumpToOffset(emojiField, 8), true);
assert.strictEqual(emojiField.value, emoji);
assert.strictEqual(emojiField.selectionStart, 8);
assert.strictEqual(emojiField.selectionEnd, 8);

const missed = manuscript(CHAPTER);
assert.strictEqual(review.jumpToOffset(missed, CHAPTER.length + 4), false);
assert.strictEqual(missed.value, CHAPTER);
assert.strictEqual(missed.focused, true);
assert.strictEqual(review.jumpToOffset(missed, null), false);
assert.strictEqual(missed.value, CHAPTER);

assert.strictEqual(
  review.anchorNote({ anchor_status: "changed", start_offset: null }),
  "This passage has changed"
);
assert.strictEqual(
  review.anchorNote({ anchor_status: "none", start_offset: null, quote: null }),
  "Can't find this passage in the chapter"
);
assert.strictEqual(
  review.anchorNote({ anchor_status: "ok", start_offset: 8, quote: ANCHOR }),
  ""
);
assert.strictEqual(review.canJump({ anchor_status: "ok", start_offset: 0 }), true);
assert.strictEqual(review.canJump({ anchor_status: "ok", start_offset: null }), false);
assert.strictEqual(review.canJump({ anchor_status: "changed", start_offset: null }), false);
assert.strictEqual(review.canJump({ anchor_status: "none", start_offset: null }), false);

const request = review.reviewRequest("/editor/moonlit-paths/1/review/", "csrf");
assert.strictEqual(request.method, "POST");
assert.strictEqual(request.body, "");
assert.strictEqual(request.url, "/editor/moonlit-paths/1/review/");
assert.ok(!JSON.stringify(request).includes(CHAPTER));

const dismiss = review.dismissRequest(
  review.dismissUrl("/editor/moonlit-paths/1/review/", 9),
  "csrf"
);
assert.strictEqual(dismiss.url, "/editor/moonlit-paths/1/findings/9/dismiss/");
assert.strictEqual(dismiss.body, "");
assert.ok(!JSON.stringify(dismiss).includes(CHAPTER));

function element(tag) {
  const node = {
    tag: tag,
    attrs: {},
    children: [],
    text: "",
    className: "",
    parentNode: null,
    focused: false,
    setAttribute(name, value) {
      this.attrs[name] = String(value);
    },
    getAttribute(name) {
      return Object.prototype.hasOwnProperty.call(this.attrs, name)
        ? this.attrs[name]
        : null;
    },
    appendChild(child) {
      child.parentNode = this;
      this.children.push(child);
    },
    focus() {
      this.focused = true;
    },
    get textContent() {
      return this.text;
    },
    set textContent(value) {
      this.text = String(value);
    },
  };
  return node;
}

function fakeDoc(content) {
  const field = manuscript(content);
  const status = element("p");
  const list = element("ol");
  const panel = element("div");
  const heading = element("h2");
  panel.hidden = true;
  const root = {
    getAttribute(name) {
      const data = {
        "data-review-url": "/editor/moonlit-paths/1/review/",
        "data-empty-chapter": NOTHING_YET,
        "data-did-not-run": FAILED,
        "data-no-questions": NO_QUESTIONS,
        "data-authorship": AUTHORSHIP,
      };
      return data[name] || null;
    },
  };
  const csrf = { value: "csrf" };
  const nodes = {
    manuscript: field,
    "review-status": status,
    "review-findings": list,
    "review-panel": panel,
    "review-heading": heading,
    "chapter-editor": root,
  };
  return {
    field: field,
    status: status,
    list: list,
    panel: panel,
    heading: heading,
    getElementById(id) {
      return nodes[id] || null;
    },
    querySelector() {
      return csrf;
    },
    createElement: element,
  };
}

function answer(body) {
  return function send(payload) {
    send.payload = payload;
    return {
      then(ok) {
        send.finish = function () {
          ok({ body: body });
        };
      },
    };
  };
}

const emptyDoc = fakeDoc("  ");
const emptySend = answer({ state: "empty" });
const emptyAction = review.beginReview(emptyDoc, emptySend);
assert.strictEqual(emptyAction.body, "");
assert.strictEqual(emptyDoc.status.text, REVIEWING);
assert.strictEqual(emptyDoc.field.value, "  ");
emptySend.finish();
assert.strictEqual(emptyDoc.panel.hidden, false);
assert.strictEqual(emptyDoc.status.text, NOTHING_YET);
assert.strictEqual(emptyDoc.field.value, "  ");
assert.strictEqual(emptyDoc.list.children.length, 0);

const calls = [];
const chapterDoc = fakeDoc(CHAPTER);
const sent = review.beginReview(chapterDoc, function send(payload) {
  calls.push(payload);
  return {
    then(ok) {
      ok({ body: null });
    },
  };
});
assert.strictEqual(sent.body, "");
assert.strictEqual(calls.length, 1);
assert.strictEqual(chapterDoc.field.value, CHAPTER);
assert.strictEqual(chapterDoc.status.text, FAILED);

const blocked = [];
const blockedDoc = fakeDoc(CHAPTER);
const blockedResult = review.beginReview(
  blockedDoc,
  function send() {
    blocked.push(send);
    return null;
  },
  function settle(doc, done) {
    done(false);
  }
);
assert.strictEqual(blockedResult, null);
assert.strictEqual(blocked.length, 0);
assert.strictEqual(
  blockedDoc.status.text,
  "Your chapter didn't save, so the review didn't run."
);
assert.strictEqual(blockedDoc.panel.hidden, false);
assert.strictEqual(blockedDoc.field.value, CHAPTER);

function rowText(item) {
  return item.children.map((child) => child.text).join("\n");
}

const shown = fakeDoc(CHAPTER);
const loaded = element("li");
loaded.text = "Loaded with the page";
shown.list.appendChild(loaded);
review.showReviewResponse(shown, {
  state: "ran",
  message: AUTHORSHIP,
  findings: [
    {
      id: 3,
      question: QUESTION,
      status: "open",
      quote: ANCHOR,
      start_offset: 0,
      anchor_status: "ok",
    },
  ],
});
assert.strictEqual(shown.field.value, CHAPTER);
assert.strictEqual(shown.panel.hidden, false);
assert.strictEqual(shown.status.text, "");
assert.strictEqual(shown.list.children.length, 1);
const item = shown.list.children[0];
assert.strictEqual(item.attrs["aria-labelledby"], "review-question-3");
assert.strictEqual(item.attrs["data-anchor-status"], "ok");
assert.strictEqual(item.attrs.tabindex, "-1");
const question = item.children.find((child) => child.attrs.id === "review-question-3");
assert.strictEqual(question.text, QUESTION);
const jump = item.children.find((child) => child.className === "review-jump");
assert.strictEqual(jump.attrs["data-start-offset"], "0");
assert.strictEqual(jump.attrs.type, "button");
assert.strictEqual(jump.attrs.disabled, undefined);
assert.ok(!rowText(item).includes(ANCHOR));
const dismissButton = item.children.find((child) => child.className === "review-dismiss");
assert.strictEqual(
  dismissButton.attrs["data-dismiss-url"],
  "/editor/moonlit-paths/1/findings/3/dismiss/"
);
assert.ok(dismissButton.attrs["aria-label"].includes(QUESTION));

let releaseReview = null;
const inFlight = review.beginReview(shown, function send() {
  return {
    then(ok) {
      releaseReview = function () {
        ok({
          body: {
            state: "ran",
            findings: [
              {
                id: 8,
                question: "What does the morning hold?",
                status: "open",
                start_offset: 4,
                anchor_status: "ok",
              },
            ],
          },
        });
      };
    },
  };
});
assert.strictEqual(shown.status.text, REVIEWING);
assert.strictEqual(inFlight.body, "");
const second = review.beginReview(shown, function send() {
  throw new Error("a second review must not start");
});
assert.strictEqual(second, null);
assert.strictEqual(shown.list.children.length, 1);
assert.strictEqual(shown.list.children[0].attrs["data-finding-id"], "3");
releaseReview();
assert.strictEqual(shown.list.children.length, 1);
assert.strictEqual(shown.list.children[0].attrs["data-finding-id"], "8");

const changed = fakeDoc(CHAPTER);
review.showReviewResponse(changed, {
  state: "ran",
  findings: [
    {
      id: 5,
      question: QUESTION,
      status: "open",
      quote: ANCHOR,
      start_offset: null,
      anchor_status: "changed",
    },
  ],
});
assert.strictEqual(changed.field.value, CHAPTER);
const changedRow = changed.list.children[0];
assert.strictEqual(
  changedRow.children.find((child) => child.className === "review-anchor-note").text,
  "This passage has changed"
);
assert.strictEqual(
  changedRow.children.find((child) => child.className === "review-jump"),
  undefined
);
assert.ok(changedRow.children.some((child) => child.className === "review-dismiss"));

const missing = fakeDoc(CHAPTER);
review.showReviewResponse(missing, {
  state: "ran",
  findings: [
    {
      id: 6,
      question: QUESTION,
      status: "open",
      quote: null,
      start_offset: null,
      anchor_status: "none",
    },
  ],
});
const missingRow = missing.list.children[0];
assert.strictEqual(
  missingRow.children.find((child) => child.className === "review-anchor-note").text,
  "Can't find this passage in the chapter"
);
assert.strictEqual(
  missingRow.children.find((child) => child.className === "review-jump"),
  undefined
);
assert.strictEqual(missing.field.value, CHAPTER);

review.showReviewResponse(shown, {
  state: "failed",
  status: "gap",
  message: GAP,
});
assert.strictEqual(shown.field.value, CHAPTER);
assert.strictEqual(shown.status.text, FAILED);
assert.ok(!shown.status.text.includes(GAP));
assert.ok(!shown.status.text.toLowerCase().includes("no gaps"));
assert.strictEqual(shown.list.children.length, 1);
assert.strictEqual(shown.list.children[0].attrs["data-finding-id"], "8");

review.showReviewResponse(shown, { state: "ran", message: GAP });
assert.strictEqual(shown.status.text, NO_QUESTIONS);
assert.strictEqual(shown.list.children.length, 0);
assert.ok(!shown.status.text.includes(GAP));
assert.strictEqual(shown.field.value, CHAPTER);

const removed = element("li");
const parent = element("ol");
parent.appendChild(removed);
review.removeFinding(removed);
assert.strictEqual(parent.children.length, 0);

function findingRow(questionText) {
  const row = element("li");
  row.className = "review-finding";
  const question = element("p");
  question.text = questionText;
  row.appendChild(question);
  return row;
}

const focusDoc = fakeDoc(CHAPTER);
const firstRow = findingRow("First question?");
const middleRow = findingRow("Middle question?");
const lastRow = findingRow("Last question?");
focusDoc.list.appendChild(firstRow);
focusDoc.list.appendChild(middleRow);
focusDoc.list.appendChild(lastRow);
review.applyDismiss(focusDoc, firstRow, { status: "dismissed" });
assert.strictEqual(middleRow.focused, true);
assert.strictEqual(focusDoc.list.children.length, 2);
assert.strictEqual(focusDoc.field.value, CHAPTER);

review.applyDismiss(focusDoc, lastRow, { status: "dismissed" });
assert.strictEqual(middleRow.focused, true);
assert.strictEqual(focusDoc.list.children.length, 1);

review.applyDismiss(focusDoc, middleRow, { status: "not-dismissed" });
assert.strictEqual(focusDoc.list.children.length, 1);
assert.strictEqual(focusDoc.status.text, DISMISS_FAILED);
assert.strictEqual(focusDoc.field.value, CHAPTER);

review.applyDismiss(focusDoc, middleRow, { status: "dismissed" });
assert.strictEqual(focusDoc.list.children.length, 0);
assert.strictEqual(focusDoc.heading.focused, true);
assert.strictEqual(CHAPTER, ANCHOR + " through the quiet valley.");
