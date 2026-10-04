function fieldValue(el) {
  return el ? el.value : "";
}

function applyAutosaveResult(successful, responseText, savedLabel) {
  var text = String(responseText == null ? "" : responseText).trim();
  if (successful && savedLabel && text === savedLabel) {
    return "saved";
  }
  return "failed";
}

function showSaveStatus(root, statusEl, state) {
  if (!root || !statusEl || !root.getAttribute) {
    return;
  }
  var label = root.getAttribute("data-label-" + state);
  if (!label) {
    return;
  }
  statusEl.dataset.status = state;
  statusEl.textContent = label;
}

function finishAutosave(input) {
  var pending =
    !!input.snapshot &&
    (input.snapshot.title !== input.title || input.snapshot.content !== input.content);
  var savedLabel = input.root.getAttribute("data-label-saved");
  var outcome = applyAutosaveResult(
    input.successful,
    input.responseText,
    savedLabel
  );
  var state = outcome === "failed" ? "failed" : pending ? "saving" : "saved";
  showSaveStatus(input.root, input.statusEl, state);
  return {
    state: state,
    title: input.title,
    content: input.content,
  };
}

function waitForField(field) {
  if (field === "title") {
    return 1000;
  }
  if (field === "body") {
    return 2000;
  }
  return 2000;
}

function decideLeave(state, pending) {
  if (state === "saved" && !pending) {
    return "navigate";
  }
  return "stay";
}

function markSaving(doc) {
  showSaveStatus(
    doc.getElementById("chapter-editor"),
    doc.getElementById("save-status"),
    "saving"
  );
}

function editorRoot(evt) {
  var elt = evt.detail && evt.detail.elt;
  if (!elt || !elt.closest) {
    return null;
  }
  return elt.closest("#chapter-editor");
}

function rememberSnapshot(evt, root) {
  if (!evt.detail || !evt.detail.xhr) {
    return;
  }
  requestSerial += 1;
  evt.detail.xhr.__editorRequest = requestSerial;
  evt.detail.xhr.__editorSnapshot = {
    title: fieldValue(root.querySelector("#chapter-title")),
    content: fieldValue(root.querySelector("#manuscript")),
  };
}

function onAutosaveStart(evt) {
  var root = editorRoot(evt);
  if (!root) {
    return;
  }
  inFlight = true;
  rememberSnapshot(evt, root);
  showSaveStatus(root, root.querySelector("#save-status"), "saving");
}

function onAutosaveFinish(evt) {
  var root = editorRoot(evt);
  if (!root) {
    return;
  }
  var xhr = evt.detail && evt.detail.xhr;
  if (!xhr || xhr.__editorSettled || xhr.__editorRequest !== requestSerial) {
    return;
  }
  xhr.__editorSettled = true;
  inFlight = false;
  var doc = root.ownerDocument || document;
  var snapshot = xhr.__editorSnapshot || null;
  var successful = !!(evt.detail && evt.detail.successful);
  var fields = currentFields(doc);
  var result = finishAutosave({
    successful: successful,
    responseText: xhr.responseText || "",
    snapshot: snapshot,
    title: fields.title,
    content: fields.content,
    root: root,
    statusEl: root.querySelector("#save-status"),
  });
  if (result.state !== "failed" && snapshot) {
    savedSnapshot = { title: snapshot.title, content: snapshot.content };
  }
  if (result.state === "failed") {
    queuedSave = false;
    if (leavingTo) {
      cancelLeave();
    }
    return;
  }
  if (isDirty(doc)) {
    queuedSave = false;
    flushSave(doc);
    return;
  }
  queuedSave = false;
  if (leavingTo && decideLeave(result.state, false) === "navigate") {
    var dest = leavingTo;
    leavingTo = null;
    onLeaveStay = null;
    window.location.assign(dest);
  }
}

var savedSnapshot = null;
var saveTimer = null;
var requestSerial = 0;
var inFlight = false;
var queuedSave = false;
var leavingTo = null;
var onLeaveStay = null;

function currentFields(doc) {
  return {
    title: fieldValue(doc.getElementById("chapter-title")),
    content: fieldValue(doc.getElementById("manuscript")),
  };
}

function isDirty(doc) {
  var fields = currentFields(doc);
  return (
    !savedSnapshot ||
    fields.title !== savedSnapshot.title ||
    fields.content !== savedSnapshot.content
  );
}

function scheduleSave(doc, field) {
  markSaving(doc);
  if (saveTimer) {
    clearTimeout(saveTimer);
  }
  saveTimer = setTimeout(function () {
    saveTimer = null;
    if (isDirty(doc)) {
      htmx.trigger(doc.getElementById("chapter-form"), "flush");
    }
  }, waitForField(field));
}

function flushSave(doc) {
  if (saveTimer) {
    clearTimeout(saveTimer);
    saveTimer = null;
  }
  if (!isDirty(doc)) {
    return;
  }
  markSaving(doc);
  if (inFlight) {
    queuedSave = true;
    return;
  }
  inFlight = true;
  htmx.trigger(doc.getElementById("chapter-form"), "flush");
}

function cancelLeave() {
  if (onLeaveStay) {
    onLeaveStay();
  }
  onLeaveStay = null;
  leavingTo = null;
}

function beginLeave(doc, url, stay) {
  leavingTo = url;
  onLeaveStay = stay || null;
  if (!isDirty(doc)) {
    leavingTo = null;
    onLeaveStay = null;
    window.location.assign(url);
    return;
  }
  flushSave(doc);
}

function onFieldInput(evt) {
  var target = evt.target;
  if (!target) {
    return;
  }
  var field = null;
  if (target.id === "chapter-title") {
    field = "title";
  } else if (target.id === "manuscript") {
    field = "body";
  }
  if (!field) {
    return;
  }
  if (!isDirty(document)) {
    if (saveTimer) {
      clearTimeout(saveTimer);
      saveTimer = null;
    }
    showSaveStatus(
      document.getElementById("chapter-editor"),
      document.getElementById("save-status"),
      "saved"
    );
    return;
  }
  scheduleSave(document, field);
}

function onBackClick(evt) {
  var target = evt.target;
  var link = target && target.closest && target.closest("#back-to-book");
  if (!link) {
    return;
  }
  if (
    evt.defaultPrevented ||
    evt.button !== 0 ||
    evt.metaKey ||
    evt.ctrlKey ||
    evt.shiftKey ||
    evt.altKey
  ) {
    return;
  }
  evt.preventDefault();
  beginLeave(document, link.href, null);
}

function onChapterChange(evt) {
  var menu = evt.target;
  if (!menu || menu.id !== "chapter-menu") {
    return;
  }
  var url = menu.value;
  var current = menu.getAttribute("data-current");
  if (!url || url === current) {
    return;
  }
  beginLeave(document, url, function () {
    var options = menu.options;
    for (var i = 0; i < options.length; i += 1) {
      options[i].selected = options[i].getAttribute("value") === current;
    }
  });
}

function bindEditor(doc) {
  savedSnapshot = currentFields(doc);
  doc.addEventListener("input", onFieldInput);
  doc.addEventListener("click", onBackClick);
  doc.addEventListener("change", onChapterChange);
  doc.addEventListener("htmx:beforeRequest", onAutosaveStart);
  doc.addEventListener("htmx:afterRequest", onAutosaveFinish);
  doc.addEventListener("htmx:sendError", onAutosaveFinish);
}

var worldsEditor = {
  applyAutosaveResult: applyAutosaveResult,
  showSaveStatus: showSaveStatus,
  finishAutosave: finishAutosave,
  markSaving: markSaving,
  waitForField: waitForField,
  decideLeave: decideLeave,
};

if (typeof window !== "undefined") {
  window.worldsEditor = worldsEditor;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = worldsEditor;
}

if (typeof document !== "undefined") {
  bindEditor(document);
}
