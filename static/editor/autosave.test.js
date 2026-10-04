const assert = require("assert");
const { applyAutosaveResult, finishAutosave, showSaveStatus } = require("./autosave.js");

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
