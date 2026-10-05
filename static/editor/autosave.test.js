const assert = require("assert");
const {
  applyAutosaveResult,
  decideLeave,
  finishAutosave,
  showSaveStatus,
  waitForField,
} = require("./autosave.js");

assert.strictEqual(waitForField("title"), 1000);
assert.strictEqual(waitForField("body"), 2000);
assert.strictEqual(decideLeave("saved", false), "navigate");
assert.strictEqual(decideLeave("saved", true), "stay");
assert.strictEqual(decideLeave("saving", true), "stay");
assert.strictEqual(decideLeave("failed", true), "stay");
assert.strictEqual(decideLeave("failed", false), "stay");

function root() {
  const labels = {
    "data-label-saving": "Saving",
    "data-label-saved": "Saved",
    "data-label-failed": "Failed",
  };
  return {
    getAttribute(name) {
      return labels[name] || null;
    },
  };
}

function statusEl() {
  return { dataset: {}, textContent: "" };
}

const kept = "The river kept its course through the quiet valley.";

assert.strictEqual(applyAutosaveResult(true, "Saved", "Saved"), "saved");
assert.strictEqual(applyAutosaveResult(true, "  Saved  ", "Saved"), "saved");
assert.strictEqual(applyAutosaveResult(false, "Saved", "Saved"), "failed");
assert.strictEqual(applyAutosaveResult(false, "Failed", "Saved"), "failed");
assert.strictEqual(applyAutosaveResult(true, "Failed", "Saved"), "failed");
assert.strictEqual(
  applyAutosaveResult(true, "Saved\n" + kept, "Saved"),
  "failed"
);
assert.strictEqual(applyAutosaveResult(true, kept, "Saved"), "failed");

const shown = statusEl();
showSaveStatus(root(), shown, "failed");
assert.strictEqual(shown.textContent, "Failed");
assert.strictEqual(shown.dataset.status, "failed");
assert.strictEqual(kept, "The river kept its course through the quiet valley.");

const failedStatus = statusEl();
const failed = finishAutosave({
  successful: false,
  responseText: "A different paragraph that must not be inserted.",
  snapshot: { title: "Dawn", content: kept },
  title: "Dawn",
  content: kept,
  root: root(),
  statusEl: failedStatus,
});
assert.strictEqual(failed.state, "failed");
assert.strictEqual(failed.content, kept);
assert.strictEqual(failed.title, "Dawn");
assert.strictEqual(failedStatus.textContent, "Failed");

const savedStatus = statusEl();
const saved = finishAutosave({
  successful: true,
  responseText: "Saved",
  snapshot: { title: "Dawn", content: kept },
  title: "Dawn",
  content: kept,
  root: root(),
  statusEl: savedStatus,
});
assert.strictEqual(saved.state, "saved");
assert.strictEqual(saved.content, kept);
assert.strictEqual(savedStatus.textContent, "Saved");

const dirtyStatus = statusEl();
const newer = kept + " Another sentence followed.";
const dirty = finishAutosave({
  successful: true,
  responseText: "Saved",
  snapshot: { title: "Dawn", content: kept },
  title: "Dawn",
  content: newer,
  root: root(),
  statusEl: dirtyStatus,
});
assert.strictEqual(dirty.state, "saving");
assert.strictEqual(dirty.content, newer);
assert.strictEqual(dirtyStatus.textContent, "Saving");

const mismatched = finishAutosave({
  successful: true,
  responseText: newer,
  snapshot: { title: "Dawn", content: newer },
  title: "Dawn",
  content: newer,
  root: root(),
  statusEl: statusEl(),
});
assert.strictEqual(mismatched.state, "failed");
assert.strictEqual(mismatched.content, newer);

const failedWhileNewer = statusEl();
const failedPending = finishAutosave({
  successful: false,
  responseText: "Failed",
  snapshot: { title: "Dawn", content: kept },
  title: "Dawn",
  content: newer,
  root: root(),
  statusEl: failedWhileNewer,
});
assert.strictEqual(failedPending.state, "failed");
assert.strictEqual(failedPending.content, newer);
assert.strictEqual(failedWhileNewer.textContent, "Failed");
assert.notStrictEqual(failedWhileNewer.textContent, "");

function editorDocument(content) {
  const handlers = {};
  const title = { value: "Dawn" };
  const manuscript = { value: content };
  const status = { dataset: {}, textContent: "Saved" };
  const editor = {
    getAttribute(name) {
      return (
        {
          "data-label-saving": "Saving",
          "data-label-saved": "Saved",
          "data-label-failed": "Failed",
        }[name] || null
      );
    },
    querySelector(selector) {
      if (selector === "#save-status") {
        return status;
      }
      if (selector === "#chapter-title") {
        return title;
      }
      if (selector === "#manuscript") {
        return manuscript;
      }
      return null;
    },
  };
  const form = {
    closest() {
      return editor;
    },
  };
  return {
    handlers,
    title,
    manuscript,
    status,
    form,
    addEventListener(type, fn) {
      handlers[type] = fn;
    },
    getElementById(id) {
      if (id === "chapter-title") {
        return title;
      }
      if (id === "manuscript") {
        return manuscript;
      }
      if (id === "save-status") {
        return status;
      }
      if (id === "chapter-editor") {
        return editor;
      }
      if (id === "chapter-form") {
        return form;
      }
      return null;
    },
  };
}

function loadEditor(doc) {
  global.document = doc;
  global.window = { location: { assign() {} } };
  global.htmx = { calls: 0, trigger() { this.calls += 1; } };
  const resolved = require.resolve("./autosave.js");
  delete require.cache[resolved];
  return require("./autosave.js");
}

function finishRequest(doc, successful, responseText) {
  const xhr = { responseText };
  const evt = { detail: { elt: doc.form, successful, xhr } };
  doc.handlers["htmx:beforeRequest"](evt);
  doc.handlers["htmx:afterRequest"](evt);
}

const settledDoc = editorDocument(kept);
const settledEditor = loadEditor(settledDoc);
let settled = null;
settledEditor.finishPendingSave(settledDoc, function (ok) {
  settled = ok;
});
assert.strictEqual(settled, true);
assert.strictEqual(global.htmx.calls, 0);

settledDoc.manuscript.value = kept + " Extra.";
settled = null;
settledEditor.finishPendingSave(settledDoc, function (ok) {
  settled = ok;
});
assert.strictEqual(settled, null);
assert.strictEqual(global.htmx.calls, 1);
assert.strictEqual(settledDoc.status.textContent, "Saving");
finishRequest(settledDoc, true, "Saved");
assert.strictEqual(settled, true);
assert.strictEqual(settledDoc.status.textContent, "Saved");

settledDoc.manuscript.value = kept + " Again.";
settled = null;
settledEditor.finishPendingSave(settledDoc, function (ok) {
  settled = ok;
});
assert.strictEqual(settled, null);
finishRequest(settledDoc, false, "Failed");
assert.strictEqual(settled, false);
assert.strictEqual(settledDoc.status.textContent, "Failed");
assert.strictEqual(settledDoc.manuscript.value, kept + " Again.");
