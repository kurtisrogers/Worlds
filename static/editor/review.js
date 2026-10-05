var FAILED = "The review did not run. Your chapter hasn't changed.";
var NO_QUESTIONS = "No questions this time. Your chapter hasn't changed.";
var NOTHING_YET = "There's nothing to review yet.";
var REVIEWING = "Reviewing…";
var DISMISS_FAILED = "Couldn't dismiss. Try again.";
var AUTHORSHIP = "This is assistance, not authorship.";
var PASSAGE_CHANGED = "This passage has changed";
var PASSAGE_MISSING = "Can't find this passage in the chapter";
var reviewBusy = false;

function isEmptyChapter(content) {
  return String(content == null ? "" : content).trim() === "";
}

function prepareReview(content) {
  if (isEmptyChapter(content)) {
    return { state: "empty" };
  }
  return { state: "request" };
}

function scrub(text) {
  var value = String(text || "");
  if (value.toLowerCase().indexOf("no gaps") !== -1) {
    return "";
  }
  return value;
}

function copyFor(copy) {
  return {
    failed: (copy && copy.failed) || FAILED,
    empty: (copy && copy.empty) || NOTHING_YET,
    noQuestions: (copy && copy.noQuestions) || NO_QUESTIONS,
    authorship: (copy && copy.authorship) || AUTHORSHIP,
  };
}

function interpretReview(body, copy) {
  var words = copyFor(copy);
  var failed = {
    state: "failed",
    message: words.failed,
    findings: [],
    replace: false,
  };
  var state = body && typeof body === "object" ? body.state : "failed";
  switch (state) {
    case "empty":
      return {
        state: "empty",
        message: words.empty,
        findings: [],
        replace: false,
      };
    case "ran":
      var findings = Array.isArray(body.findings) ? body.findings : [];
      return {
        state: "ran",
        message: findings.length ? words.authorship : words.noQuestions,
        findings: findings,
        replace: true,
      };
    case "failed":
      return failed;
    default:
      return failed;
  }
}

function canJump(finding) {
  return !!(
    finding &&
    finding.anchor_status === "ok" &&
    finding.start_offset !== null &&
    finding.start_offset !== undefined &&
    finding.start_offset !== ""
  );
}

function anchorNote(finding) {
  if (!finding || canJump(finding)) {
    return "";
  }
  if (finding.anchor_status === "changed") {
    return PASSAGE_CHANGED;
  }
  if (finding.anchor_status === "none") {
    return PASSAGE_MISSING;
  }
  return "";
}

function scrollCaretIntoView(manuscript, offset) {
  var doc = manuscript.ownerDocument;
  var view = doc && doc.defaultView;
  if (!doc || !view || !view.getComputedStyle || !manuscript.parentNode) {
    return;
  }
  var style = view.getComputedStyle(manuscript);
  var mirror = doc.createElement("div");
  var names = [
    "boxSizing",
    "width",
    "fontFamily",
    "fontSize",
    "fontWeight",
    "fontStyle",
    "letterSpacing",
    "lineHeight",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "borderTopWidth",
    "borderRightWidth",
    "borderBottomWidth",
    "borderLeftWidth",
    "whiteSpace",
    "wordWrap",
    "overflowWrap",
  ];
  mirror.style.position = "absolute";
  mirror.style.left = "-9999px";
  mirror.style.top = "0";
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre-wrap";
  for (var index = 0; index < names.length; index += 1) {
    mirror.style[names[index]] = style[names[index]];
  }
  mirror.textContent = String(manuscript.value).slice(0, offset);
  var marker = doc.createElement("span");
  marker.textContent = "\u200b";
  mirror.appendChild(marker);
  manuscript.parentNode.appendChild(mirror);
  var top = marker.offsetTop - manuscript.clientHeight / 3;
  manuscript.scrollTop = top > 0 ? top : 0;
  mirror.parentNode.removeChild(mirror);
}

function jumpToOffset(manuscript, offset) {
  if (!manuscript || offset === null || offset === undefined || offset === "") {
    return false;
  }
  var index = Number(offset);
  if (!isFinite(index) || index < 0 || Math.floor(index) !== index) {
    return false;
  }
  var value = String(manuscript.value);
  if (manuscript.focus) {
    manuscript.focus();
  }
  if (index > value.length) {
    return false;
  }
  if (manuscript.setSelectionRange) {
    manuscript.setSelectionRange(index, index);
  } else {
    manuscript.selectionStart = index;
    manuscript.selectionEnd = index;
  }
  scrollCaretIntoView(manuscript, index);
  return (
    manuscript.value === value &&
    manuscript.selectionStart === index &&
    manuscript.selectionEnd === index
  );
}

function postJson(url, token) {
  return {
    url: url,
    method: "POST",
    body: "",
    headers: {
      "X-CSRFToken": token || "",
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  };
}

function reviewRequest(url, token) {
  return postJson(url, token);
}

function dismissRequest(url, token) {
  return postJson(url, token);
}

function dismissUrl(reviewUrl, id) {
  var base = String(reviewUrl || "");
  if (base.charAt(base.length - 1) !== "/") {
    base += "/";
  }
  return base.replace(/review\/$/, "findings/" + id + "/dismiss/");
}

function csrfToken(doc) {
  var input = doc.querySelector(
    "#chapter-form input[name='csrfmiddlewaretoken']"
  );
  return input && input.value ? input.value : "";
}

function pageCopy(doc) {
  var root = doc.getElementById("chapter-editor");
  function read(name, fallback) {
    var value = root && root.getAttribute(name);
    return value || fallback;
  }
  return {
    empty: read("data-empty-chapter", NOTHING_YET),
    failed: read("data-did-not-run", FAILED),
    noQuestions: read("data-no-questions", NO_QUESTIONS),
    authorship: read("data-authorship", AUTHORSHIP),
  };
}

function viewFrom(doc) {
  var root = doc.getElementById("chapter-editor");
  return {
    doc: doc,
    manuscript: doc.getElementById("manuscript"),
    panel: doc.getElementById("review-panel"),
    statusEl: doc.getElementById("review-status"),
    list: doc.getElementById("review-findings"),
    reviewUrl: root ? root.getAttribute("data-review-url") : "",
  };
}

function createFinding(doc, finding, reviewUrl) {
  var item = doc.createElement("li");
  item.className = "review-finding";
  item.setAttribute("data-finding-id", finding.id);
  item.setAttribute("data-anchor-status", finding.anchor_status || "");
  item.setAttribute("tabindex", "-1");
  var questionId = "review-question-" + finding.id;
  item.setAttribute("aria-labelledby", questionId);
  var question = doc.createElement("p");
  question.className = "review-question";
  question.setAttribute("id", questionId);
  question.textContent = scrub(finding.question || "");
  item.appendChild(question);
  var note = anchorNote(finding);
  if (note) {
    var noteEl = doc.createElement("p");
    noteEl.className = "review-anchor-note";
    noteEl.textContent = note;
    item.appendChild(noteEl);
  }
  if (canJump(finding)) {
    var jump = doc.createElement("button");
    jump.className = "review-jump";
    jump.setAttribute("type", "button");
    jump.setAttribute("data-start-offset", String(finding.start_offset));
    jump.setAttribute("aria-label", "Jump to " + (finding.question || ""));
    jump.textContent = "Jump";
    item.appendChild(jump);
  }
  var dismiss = doc.createElement("button");
  dismiss.className = "review-dismiss";
  dismiss.setAttribute("type", "button");
  dismiss.setAttribute("data-dismiss-url", dismissUrl(reviewUrl, finding.id));
  dismiss.setAttribute("aria-label", "Dismiss " + (finding.question || ""));
  dismiss.textContent = "Dismiss";
  item.appendChild(dismiss);
  return item;
}

function clearFindings(list) {
  if (!list || !list.children) {
    return;
  }
  while (list.children.length) {
    var child = list.children[0];
    if (typeof list.removeChild === "function") {
      list.removeChild(child);
    } else if (typeof list.children.splice === "function") {
      list.children.splice(0, 1);
      child.parentNode = null;
    } else {
      return;
    }
  }
}

function presentReview(view, outcome) {
  if (!view.panel || !view.statusEl) {
    return;
  }
  view.panel.hidden = false;
  view.statusEl.textContent = outcome.message || "";
  if (!outcome.replace || !view.list) {
    return;
  }
  clearFindings(view.list);
  var findings = outcome.findings || [];
  for (var index = 0; index < findings.length; index += 1) {
    view.list.appendChild(
      createFinding(view.doc, findings[index], view.reviewUrl)
    );
  }
}

function showReviewResponse(doc, body) {
  var view = viewFrom(doc);
  var before = view.manuscript ? view.manuscript.value : "";
  presentReview(view, interpretReview(body, pageCopy(doc)));
  if (view.manuscript && view.manuscript.value !== before) {
    throw new Error("review wrote the manuscript");
  }
}

function defaultSend(request) {
  return fetch(request.url, {
    method: request.method,
    headers: request.headers,
    body: request.body,
    credentials: "same-origin",
  }).then(
    function (response) {
      return response.json().then(
        function (body) {
          return { body: body };
        },
        function () {
          return { body: null };
        }
      );
    },
    function () {
      return { body: null };
    }
  );
}

function defaultSettle(doc, done) {
  var editor = typeof window !== "undefined" ? window.worldsEditor : null;
  if (editor && typeof editor.finishPendingSave === "function") {
    editor.finishPendingSave(doc, done);
    return;
  }
  done(true);
}

function beginReview(doc, send, settle) {
  if (reviewBusy) {
    return null;
  }
  reviewBusy = true;
  var request = null;
  var wait = settle || defaultSettle;
  wait(doc, function (saved) {
    if (!reviewBusy) {
      return;
    }
    if (!saved) {
      reviewBusy = false;
      return;
    }
    var view = viewFrom(doc);
    if (view.panel) {
      view.panel.hidden = false;
    }
    if (view.statusEl) {
      view.statusEl.textContent = REVIEWING;
    }
    var manuscript = doc.getElementById("manuscript");
    var before = manuscript ? manuscript.value : "";
    var root = doc.getElementById("chapter-editor");
    request = reviewRequest(
      root ? root.getAttribute("data-review-url") : "",
      csrfToken(doc)
    );
    var deliver = send || defaultSend;
    var pending = deliver(request);
    var finish = function (result) {
      reviewBusy = false;
      showReviewResponse(doc, result && result.body);
      if (manuscript && manuscript.value !== before) {
        throw new Error("review wrote the manuscript");
      }
    };
    if (pending && typeof pending.then === "function") {
      pending.then(finish, function () {
        reviewBusy = false;
        showReviewResponse(doc, null);
      });
    } else {
      finish(pending);
    }
  });
  return request;
}

function removeFinding(item) {
  if (!item || !item.parentNode) {
    return;
  }
  var parent = item.parentNode;
  if (parent.removeChild) {
    parent.removeChild(item);
    return;
  }
  if (parent.children && parent.children.indexOf) {
    var index = parent.children.indexOf(item);
    if (index !== -1) {
      parent.children.splice(index, 1);
    }
  }
  item.parentNode = null;
}

function rowAt(parent, index) {
  if (!parent || !parent.children || index < 0 || index >= parent.children.length) {
    return null;
  }
  return parent.children[index];
}

function indexOfRow(item) {
  var parent = item && item.parentNode;
  if (!parent || !parent.children) {
    return -1;
  }
  for (var index = 0; index < parent.children.length; index += 1) {
    if (parent.children[index] === item) {
      return index;
    }
  }
  return -1;
}

function focusElement(el) {
  if (el && typeof el.focus === "function") {
    el.focus();
  }
}

function applyDismiss(doc, item, body) {
  if (body && body.status === "dismissed") {
    var parent = item ? item.parentNode : null;
    var index = indexOfRow(item);
    var next = rowAt(parent, index + 1);
    var previous = rowAt(parent, index - 1);
    removeFinding(item);
    if (next && next.parentNode) {
      focusElement(next);
      return;
    }
    if (previous && previous.parentNode) {
      focusElement(previous);
      return;
    }
    focusElement(doc.getElementById("review-heading"));
    return;
  }
  var status = doc.getElementById("review-status");
  if (status) {
    status.textContent = DISMISS_FAILED;
  }
}

function onClick(evt) {
  var target = evt.target;
  if (!target || !target.closest) {
    return;
  }
  var doc = target.ownerDocument || document;
  if (target.closest("#review-chapter")) {
    beginReview(doc);
    return;
  }
  var jump = target.closest(".review-jump");
  if (jump) {
    var offset = jump.getAttribute("data-start-offset");
    if (offset !== null && offset !== "") {
      jumpToOffset(doc.getElementById("manuscript"), offset);
    }
    return;
  }
  var dismiss = target.closest(".review-dismiss");
  if (!dismiss) {
    return;
  }
  var manuscript = doc.getElementById("manuscript");
  var before = manuscript ? manuscript.value : "";
  var item = dismiss.closest(".review-finding");
  defaultSend(
    dismissRequest(dismiss.getAttribute("data-dismiss-url"), csrfToken(doc))
  ).then(function (result) {
    applyDismiss(doc, item, result && result.body);
    if (manuscript && manuscript.value !== before) {
      throw new Error("dismiss wrote the manuscript");
    }
  });
}

function bindReview(doc) {
  doc.addEventListener("click", onClick);
}

var worldsReview = {
  isEmptyChapter: isEmptyChapter,
  prepareReview: prepareReview,
  interpretReview: interpretReview,
  canJump: canJump,
  anchorNote: anchorNote,
  jumpToOffset: jumpToOffset,
  reviewRequest: reviewRequest,
  dismissRequest: dismissRequest,
  dismissUrl: dismissUrl,
  beginReview: beginReview,
  showReviewResponse: showReviewResponse,
  removeFinding: removeFinding,
  applyDismiss: applyDismiss,
  clearFindings: clearFindings,
};

if (typeof window !== "undefined") {
  window.worldsReview = worldsReview;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = worldsReview;
}

if (typeof document !== "undefined") {
  bindReview(document);
}
