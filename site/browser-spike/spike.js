(function () {
  "use strict";

  var status = document.getElementById("status");
  var verdict = document.getElementById("verdict");
  var message = document.getElementById("message");
  var raw = document.getElementById("raw");
  var inputBox = document.getElementById("input-json");
  var policy = null;

  function setStatus(text, kind) {
    status.textContent = text;
    status.dataset.kind = kind || "";
  }

  function showOutcome(outcome, input) {
    verdict.hidden = false;
    verdict.dataset.kind = outcome.passed ? "pass" : "fail";
    verdict.textContent = outcome.passed ? "Pass" : "Fail";
    message.textContent = outcome.message;
    raw.textContent = JSON.stringify({ input: input, result: outcome.raw || outcome }, null, 2);
    setStatus("Evaluated in this tab. Nothing was uploaded.", "ok");
  }

  function fail(err) {
    verdict.hidden = false;
    verdict.dataset.kind = "error";
    verdict.textContent = "Error";
    message.textContent = err && err.message ? err.message : String(err);
    raw.textContent = "";
    setStatus("Evaluation did not finish.", "error");
  }

  function readInput() {
    try {
      return JSON.parse(inputBox.value);
    } catch (err) {
      throw new Error("Input JSON is not valid.");
    }
  }

  function evaluate() {
    if (!policy) {
      fail(new Error("WASM policy is still loading."));
      return;
    }
    try {
      var input = readInput();
      var rawResult = policy.evaluate(input, "enact/login_lockout/result");
      showOutcome(window.EnactOpa.interpretResult(rawResult), input);
    } catch (err) {
      fail(err);
    }
  }

  function loadSample(path) {
    return fetch(path, { cache: "no-store" }).then(function (res) {
      if (!res.ok) {
        throw new Error("Could not load " + path);
      }
      return res.json();
    }).then(function (data) {
      inputBox.value = JSON.stringify(data, null, 2);
      evaluate();
    });
  }

  document.getElementById("run-pass").addEventListener("click", function () {
    loadSample("./samples/passing.json").catch(fail);
  });
  document.getElementById("run-fail").addEventListener("click", function () {
    loadSample("./samples/failing.json").catch(fail);
  });
  document.getElementById("run-custom").addEventListener("click", evaluate);

  setStatus("Loading vendored policy.wasm…");
  fetch("./policy.wasm", { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) {
        throw new Error("Could not fetch policy.wasm from this origin.");
      }
      return res.arrayBuffer();
    })
    .then(function (bytes) {
      return window.EnactOpa.loadPolicy(bytes);
    })
    .then(function (loaded) {
      policy = loaded;
      setStatus("Ready. Samples stay in this tab; wasm loaded from this site only.", "ok");
    })
    .catch(fail);
})();
