#!/usr/bin/env node
"use strict";

const assert = require("assert");
const path = require("path");
const Guide = require(path.join(__dirname, "..", "site", "guide.js"));
const Enact = require(path.join(__dirname, "..", "site", "enact.js"));
const library = require(path.join(__dirname, "..", "site", "library.json"));

function selectedFromExample(sample) {
  const selected = {};
  sample.checks.checks.forEach(function (check) {
    selected[check.rule_id] = { enabled: true, control_id: check.control_id, params: {} };
  });
  library.checks.forEach(function (check) {
    if (!selected[check.rule_id]) {
      selected[check.rule_id] = { enabled: false, control_id: "", params: {} };
    }
  });
  return selected;
}

function main() {
  const sample = library.samples["access-control"];
  assert.ok(sample, "bundled access-control sample");
  const bundle = Enact.loadBundle([sample.catalog]);
  const selected = selectedFromExample(sample);

  const summary = Guide.exampleLoadSummary({
    title: "Access-control example is ready",
    controls: bundle.controls,
    libraryChecks: library.checks,
    selected: selected,
    evidenceName: "passing.json",
  });
  assert.strictEqual(summary.controlCount, 4);
  assert.strictEqual(summary.checkCount, 4);
  assert.strictEqual(summary.evidenceKind, "passing sample");
  assert.strictEqual(summary.nextAction, "Run the assessment");
  assert.ok(summary.checkTitles.some(function (title) {
    return /lock/i.test(title) || title.indexOf("lockout") !== -1;
  }));

  const classified = Guide.classifyLibraryChecks(
    library.checks,
    selected,
    bundle.controls,
    Enact.suggestControl
  );
  assert.strictEqual(classified.used.length, 4);
  assert.ok(classified.unused.length >= 6);
  const lockout = classified.used.find(function (item) {
    return item.check.rule_id === "ac-login-lockout";
  });
  assert.ok(lockout, "lockout is selected for the example");
  assert.strictEqual(lockout.controlId, "c-ac-7");
  assert.ok(/c-ac-7/.test(lockout.reason.text));
  const unusedLogging = classified.unused.find(function (item) {
    return item.check.rule_id === "au-log-retention";
  });
  assert.ok(unusedLogging);
  assert.strictEqual(unusedLogging.reason.kind, "none");

  const rows = Guide.evidenceRows(sample.passing, {
    libraryChecks: library.checks,
    selected: selected,
    controls: bundle.controls,
  });
  assert.ok(rows.length >= 3);
  const review = rows.find(function (row) {
    return row.setting === "account_review_days";
  });
  assert.ok(review);
  assert.strictEqual(review.value, 30);
  assert.strictEqual(String(review.limit), "90");
  assert.strictEqual(review.status, "within");
  const privileged = rows.find(function (row) {
    return row.setting === "privileged_review_days";
  });
  assert.ok(privileged);
  assert.ok(/sign-off/i.test(privileged.statusLabel));

  const failRows = Guide.evidenceRows(sample.failing, {
    libraryChecks: library.checks,
    selected: selected,
    controls: bundle.controls,
  });
  const failLockout = failRows.find(function (row) {
    return row.setting === "lockout_threshold";
  });
  assert.strictEqual(failLockout.status, "over");

  const enabled = library.checks.filter(function (check) {
    return selected[check.rule_id] && selected[check.rule_id].enabled;
  });
  const help = Guide.evidenceHelp(enabled);
  assert.ok(/IAM/i.test(help));
  assert.ok(help.indexOf("account_review_days") !== -1);
  assert.ok(help.indexOf("lockout_threshold") !== -1);

  const manual = Guide.resultGuidance({
    status: "not_automated",
    check_type: "manual",
    message: "Signed access agreements for every user with a system account.",
    control_id: "c-ac-8",
  });
  assert.strictEqual(manual.label, "Need evidence");
  assert.ok(/person must confirm/i.test(manual.next));

  const hybrid = Guide.resultGuidance({
    status: "needs_evidence",
    check_type: "hybrid",
    message: "Reviewer sign-off that the privileged-account listing was examined.",
    control_id: "c-ac-2p",
    rule_id: "ac-privileged-review",
  });
  assert.strictEqual(hybrid.label, "Need evidence");
  assert.ok(/sign off/i.test(hybrid.next));
  assert.ok(/intentional/i.test(hybrid.next));

  const passed = Guide.resultGuidance({ status: "pass", check_type: "automated" });
  assert.strictEqual(passed.label, "Passed");
  assert.ok(/no further action/i.test(passed.next));

  assert.ok(Guide.glossaryTip("OSCAL"));
  assert.ok(Guide.glossaryTip("Component Definition"));
  assert.ok(Guide.termHtml("OSCAL").indexOf("term__tip") !== -1);
  assert.strictEqual(Guide.statusLabel("needs_evidence"), "Need evidence");
  assert.strictEqual(Guide.statusLabel("not_automated"), "Need evidence");

  const progress = Guide.progressFromState({
    controls: bundle.controls,
    selected: selected,
    evidenceName: "passing.json",
    hasResult: false,
  });
  assert.strictEqual(progress.catalog, "4 controls");
  assert.strictEqual(progress.checks, "4 selected");
  assert.strictEqual(progress.evidence, "passing.json");
  assert.strictEqual(progress.run, "Not yet");

  process.stdout.write("ok\n");
}

main();
