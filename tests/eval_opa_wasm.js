#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const spike = path.join(__dirname, "..", "site", "browser-spike");
const { loadPolicy, interpretResult } = require(path.join(spike, "opa-eval.js"));

async function main() {
  const wasmPath = process.argv[2];
  const inputPath = process.argv[3];
  const entrypoint = process.argv[4] || "enact/login_lockout/result";
  const wasm = fs.readFileSync(wasmPath);
  const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  const policy = await loadPolicy(wasm);
  const raw = policy.evaluate(input, entrypoint);
  process.stdout.write(JSON.stringify(interpretResult(raw)));
}

main().catch(function (err) {
  console.error(err);
  process.exit(1);
});
