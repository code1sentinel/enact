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

  assert.strictEqual(Guide.typeLabel("manual"), "Need evidence");
  assert.ok(Guide.typeLabel("manual").indexOf("Needs a person") === -1);
  assert.strictEqual(Guide.statusLabel("needs_evidence"), "Need evidence");
  assert.strictEqual(Guide.statusLabel("not_automated"), "Need evidence");

  const manualWhy = "Signed access agreements for every user with a system account.";
  const manual = Guide.resultGuidance({
    status: "not_automated",
    check_type: "manual",
    message: manualWhy,
    control_id: "c-ac-8",
  });
  assert.strictEqual(manual.label, "Need evidence");
  assert.ok(manual.next.indexOf(manualWhy) === -1, "next step must not repeat why");
  assert.ok(manual.next.length <= 90, "next step stays short");
  assert.ok(/confirm|paperwork|person/i.test(manual.next));

  const hybridWhy = "Reviewer sign-off that the privileged-account listing was examined.";
  const hybrid = Guide.resultGuidance({
    status: "needs_evidence",
    check_type: "hybrid",
    message: hybridWhy,
    control_id: "c-ac-2p",
    rule_id: "ac-privileged-review",
  });
  assert.strictEqual(hybrid.label, "Need evidence");
  assert.ok(hybrid.next.indexOf(hybridWhy) === -1, "next step must not repeat why");
  assert.ok(hybrid.next.length <= 90, "next step stays short");
  assert.ok(/sign.off/i.test(hybrid.next));

  const passed = Guide.resultGuidance({ status: "pass", check_type: "automated" });
  assert.strictEqual(passed.label, "Passed");
  assert.ok(/no further action/i.test(passed.next));
  assert.ok(passed.next.length <= 90);

  assert.ok(Guide.glossaryTip("OSCAL"));
  assert.ok(Guide.glossaryTip("POA&M"));
  assert.ok(Guide.glossaryTip("Draft"));
  assert.ok(Guide.glossaryTip("Need evidence"));
  assert.ok(Guide.glossaryTip("assessment-results.json"));
  assert.ok(Guide.glossaryTip("poam.json"));
  assert.ok(Guide.glossaryTip("Component Definition"));
  assert.ok(Guide.termHtml("OSCAL").indexOf("term__tip") !== -1);

  const preview = Guide.oscalReadableSummary({
    oscal: {
      "assessment-results": {
        metadata: {
          title: "Access-control example (passing)",
          "oscal-version": "1.1.2",
          "last-modified": "2026-10-03T12:00:02Z",
        },
        results: [
          {
            observations: [{ uuid: "o1" }, { uuid: "o2" }, { uuid: "o3" }, { uuid: "o4" }],
            findings: [{ uuid: "f1" }, { uuid: "f2" }],
          },
        ],
      },
    },
    outcomes: [
      { control_id: "c-ac-2", rule_id: "ac-account-review", status: "pass", message: "30 days" },
      { control_id: "c-ac-7", rule_id: "ac-login-lockout", status: "pass", message: "3 tries" },
      { control_id: "c-ac-8", rule_id: "ac-access-agreements", status: "not_automated", message: manualWhy },
      { control_id: "c-ac-2p", rule_id: "ac-privileged-review", status: "needs_evidence", message: hybridWhy },
    ],
  });
  assert.strictEqual(preview.title, "Access-control example (passing)");
  assert.strictEqual(preview.oscalVersion, "1.1.2");
  assert.strictEqual(preview.observationCount, 4);
  assert.strictEqual(preview.findingCount, 2);
  assert.strictEqual(preview.counts.pass, 2);
  assert.strictEqual(preview.counts.needEvidence, 2);
  assert.strictEqual(preview.counts.fail, 0);
  assert.ok(preview.facts.some(function (fact) {
    return fact.label === "OSCAL version" && fact.value === "1.1.2";
  }));
  assert.strictEqual(preview.rows[2].label, "Need evidence");
  assert.ok(preview.lede.indexOf("Need evidence") !== -1);

  assert.strictEqual(Guide.collapseSecondary("catalog"), false);
  assert.strictEqual(Guide.collapseSecondary("checks"), true);
  assert.strictEqual(Guide.collapseSecondary("evidence"), true);
  assert.strictEqual(Guide.collapseSecondary("run"), true);

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
