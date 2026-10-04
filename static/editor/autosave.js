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
  var state = pending
    ? "saving"
    : applyAutosaveResult(input.successful, input.responseText, savedLabel);
  showSaveStatus(input.root, input.statusEl, state);
  return {
    state: state,
    title: input.title,
    content: input.content,
  };
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
  rememberSnapshot(evt, root);
  showSaveStatus(root, root.querySelector("#save-status"), "saving");
}

function onAutosaveFinish(evt) {
  var root = editorRoot(evt);
  if (!root) {
    return;
  }
  var xhr = evt.detail && evt.detail.xhr;
  var snapshot = xhr ? xhr.__editorSnapshot : null;
  finishAutosave({
    successful: !!(evt.detail && evt.detail.successful),
    responseText: xhr ? xhr.responseText : "",
    snapshot: snapshot,
    title: fieldValue(root.querySelector("#chapter-title")),
    content: fieldValue(root.querySelector("#manuscript")),
    root: root,
    statusEl: root.querySelector("#save-status"),
  });
}

function bindEditor(doc) {
  doc.addEventListener("htmx:beforeRequest", onAutosaveStart);
  doc.addEventListener("htmx:afterRequest", onAutosaveFinish);
  doc.addEventListener("htmx:sendError", onAutosaveFinish);
}

var worldsEditor = {
  applyAutosaveResult: applyAutosaveResult,
  showSaveStatus: showSaveStatus,
  finishAutosave: finishAutosave,
  markSaving: markSaving,
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
