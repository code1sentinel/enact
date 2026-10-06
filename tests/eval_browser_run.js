#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const { loadPolicy } = require(path.join(__dirname, "..", "site", "opa-eval.js"));
const Enact = require(path.join(__dirname, "..", "site", "enact.js"));

async function main() {
  const wasmPath = process.argv[2];
  const catalogPath = process.argv[3];
  const checksPath = process.argv[4];
  const evidencePath = process.argv[5];
  const started = process.argv[6];
  const ended = process.argv[7];
  const title = process.argv[8];
  const libraryPath = process.argv[9] || path.join(__dirname, "..", "site", "library.json");
  const policy = await loadPolicy(fs.readFileSync(wasmPath));
  const library = JSON.parse(fs.readFileSync(libraryPath, "utf8"));
  const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
  const checks = JSON.parse(fs.readFileSync(checksPath, "utf8"));
  const evidence = JSON.parse(fs.readFileSync(evidencePath, "utf8"));
  const result = await Enact.runAssessment({
    catalog: catalog,
    checks: checks,
    evidence: evidence,
    policy: policy,
    library: library,
    title: title,
    startedIso: started,
    endedIso: ended,
    inputLabel: evidencePath,
  });
  process.stdout.write(
    JSON.stringify({
      oscal: result.oscal,
      poam: result.poam,
      html: result.html,
      counts: result.counts,
      outcomes: result.outcomes,
    })
  );
}

main().catch(function (err) {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
