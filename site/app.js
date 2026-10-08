(function () {
  "use strict";

  var library = window.ENACT_LIBRARY || { checks: [], samples: {} };
  var Guide = window.EnactGuide;
  var policy = null;
  var themeCss = "";
  var themeJs = "";
  var evidenceView = "table";
  var state = {
    step: "catalog",
    catalog: null,
    catalogName: "",
    bundle: null,
    checksDoc: null,
    checksName: "",
    evidence: null,
    evidenceName: "",
    selected: {},
    result: null,
    exampleLoaded: false,
  };

  var banner = document.getElementById("banner");
  var statusEl = document.getElementById("engine-status");

  function showBanner(text, kind) {
    if (!text) {
      banner.hidden = true;
      banner.textContent = "";
      return;
    }
    banner.hidden = false;
    banner.textContent = text;
    banner.dataset.kind = kind || "";
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.dataset.kind = kind || "";
  }

  function enabledChecks() {
    return (library.checks || []).filter(function (check) {
      return state.selected[check.rule_id] && state.selected[check.rule_id].enabled;
    });
  }

  function renderProgress() {
    var progress = Guide.progressFromState({
      controls: state.bundle ? state.bundle.controls : {},
      selected: state.selected,
      evidenceName: state.evidenceName || "",
      hasResult: Boolean(state.result),
    });
    document.getElementById("progress-catalog").textContent = progress.catalog;
    document.getElementById("progress-checks").textContent = progress.checks;
    document.getElementById("progress-evidence").textContent = progress.evidence;
    document.getElementById("progress-run").textContent = progress.run;
  }

  function renderLoadSummary() {
    var box = document.getElementById("load-summary");
    var ready = Boolean(state.bundle && state.evidence && enabledChecks().length);
    if (!ready) {
      box.hidden = true;
      return;
    }
    var summary = Guide.exampleLoadSummary({
      title: state.exampleLoaded ? "Access-control example is ready" : "Ready to run",
      controls: state.bundle.controls,
      libraryChecks: library.checks,
      selected: state.selected,
      evidenceName: state.evidenceName,
    });
    document.getElementById("load-summary-title").textContent = summary.title;
    document.getElementById("load-summary-lede").textContent =
      "Loaded " +
      summary.controlCount +
      " controls and these checks: " +
      summary.checkTitles.join("; ") +
      ". Evidence: " +
      summary.evidenceKind +
      " (" +
      summary.evidenceName +
      ").";
    var counts = document.getElementById("load-summary-counts");
    counts.innerHTML =
      "<li><strong>" +
      summary.controlCount +
      "</strong>controls</li><li><strong>" +
      summary.checkCount +
      "</strong>checks</li><li><strong>1</strong>" +
      Guide.escapeHtml(summary.evidenceKind) +
      "</li>";
    document.getElementById("load-summary-hint").textContent = summary.nextHint;
    document.getElementById("run-from-summary").textContent = summary.nextAction;
    box.hidden = false;
  }

  function go(step) {
    state.step = step;
    ["catalog", "checks", "evidence", "run"].forEach(function (name) {
      document.getElementById("step-" + name).hidden = name !== step;
      var btn = document.querySelector('.stepper [data-go="' + name + '"]');
      if (btn) {
        if (name === step) {
          btn.setAttribute("aria-current", "step");
        } else {
          btn.removeAttribute("aria-current");
        }
      }
    });
    if (step === "catalog") {
      renderLoadSummary();
    }
    if (step === "checks") {
      renderChecks();
    }
    if (step === "evidence") {
      renderEvidence();
    }
    if (step === "run") {
      renderRun();
    }
    renderProgress();
  }

  function readFile(input) {
    return new Promise(function (resolve, reject) {
      var file = input.files && input.files[0];
      if (!file) {
        reject(new Error("Choose a JSON file on this machine."));
        return;
      }
      var reader = new FileReader();
      reader.onload = function () {
        try {
          resolve({ name: file.name, data: JSON.parse(String(reader.result || "")) });
        } catch (err) {
          reject(new Error("That file is not valid JSON."));
        }
      };
      reader.onerror = function () {
        reject(new Error("Could not read that file in this tab."));
      };
      reader.readAsText(file);
    });
  }

  function setCatalog(data, name) {
    state.catalog = data;
    state.catalogName = name || "catalog.json";
    state.bundle = window.Enact.loadBundle([data]);
    state.result = null;
    var title = (state.bundle.titles && state.bundle.titles[0]) || state.catalogName;
    var count = Object.keys(state.bundle.controls).length;
    document.getElementById("catalog-empty").hidden = true;
    document.getElementById("catalog-summary").hidden = false;
    document.getElementById("catalog-title").textContent = title;
    document.getElementById("catalog-meta").textContent =
      count + " controls · opened as " + state.catalogName + " · stayed in this tab";
    var list = document.getElementById("catalog-controls");
    list.innerHTML = "";
    Object.keys(state.bundle.controls)
      .slice(0, 12)
      .forEach(function (id) {
        var item = document.createElement("li");
        item.innerHTML = "<code>" + id + "</code> — " + (state.bundle.controls[id].title || "");
        list.appendChild(item);
      });
    if (count > 12) {
      var more = document.createElement("li");
      more.textContent = "and " + (count - 12) + " more";
      list.appendChild(more);
    }
    document.getElementById("catalog-file-name").textContent = state.catalogName;
    if (!state.checksDoc) {
      seedLibrarySelection();
    }
    renderLoadSummary();
    renderProgress();
    showBanner("");
  }

  function seedLibrarySelection() {
    var selected = {};
    (library.checks || []).forEach(function (check) {
      var controlId = window.Enact.suggestControl(check, state.bundle.controls);
      selected[check.rule_id] = {
        enabled: Boolean(controlId),
        control_id: controlId || "",
        params: {},
      };
      (check.params || []).forEach(function (param) {
        selected[check.rule_id].params[param.id] = param.values && param.values[0] ? param.values[0] : "";
      });
    });
    state.selected = selected;
    state.checksDoc = null;
    state.checksName = "";
  }

  function useExample() {
    var sample = library.samples && library.samples["access-control"];
    if (!sample) {
      showBanner("Bundled example is missing from this site build.", "error");
      return;
    }
    setCatalog(sample.catalog, "access-control/catalog.json");
    state.checksDoc = sample.checks;
    state.checksName = "access-control/checks.json";
    state.evidence = sample.passing;
    state.evidenceName = "passing.json";
    state.exampleLoaded = true;
    var selected = {};
    sample.checks.checks.forEach(function (check) {
      selected[check.rule_id] = {
        enabled: true,
        control_id: check.control_id,
        params: {},
      };
    });
    (library.checks || []).forEach(function (check) {
      if (!selected[check.rule_id]) {
        selected[check.rule_id] = { enabled: false, control_id: "", params: {} };
      }
    });
    state.selected = selected;
    renderEvidence();
    renderLoadSummary();
    renderProgress();
    showBanner("");
  }

  function bindCheckCard(card) {
    card.querySelectorAll("[data-enable]").forEach(function (box) {
      box.addEventListener("change", function () {
        var id = box.getAttribute("data-enable");
        state.selected[id] = state.selected[id] || { enabled: false, control_id: "", params: {} };
        state.selected[id].enabled = box.checked;
        state.checksDoc = null;
        state.exampleLoaded = false;
        renderChecks();
        renderLoadSummary();
        renderProgress();
      });
    });
    card.querySelectorAll("[data-control]").forEach(function (select) {
      select.addEventListener("change", function () {
        var id = select.getAttribute("data-control");
        state.selected[id] = state.selected[id] || { enabled: false, control_id: "", params: {} };
        state.selected[id].control_id = select.value;
        state.checksDoc = null;
        renderChecks();
        renderProgress();
      });
    });
    card.querySelectorAll("[data-param]").forEach(function (input) {
      input.addEventListener("input", function () {
        var parts = input.getAttribute("data-param").split(":");
        var id = parts[0];
        var paramId = parts.slice(1).join(":");
        state.selected[id] = state.selected[id] || { enabled: false, control_id: "", params: {} };
        state.selected[id].params[paramId] = input.value;
      });
    });
  }

  function renderCheckCard(item, unused) {
    var check = item.check;
    var sel = state.selected[check.rule_id] || { enabled: false, control_id: "", params: {} };
    var card = document.createElement("article");
    card.className = "check" + (unused ? " check--unused" : " check--used");
    var controls = state.bundle ? Object.keys(state.bundle.controls) : [];
    var options = ['<option value="">—</option>']
      .concat(
        controls.map(function (id) {
          var chosen = sel.control_id === id ? " selected" : "";
          return (
            '<option value="' +
            id +
            '"' +
            chosen +
            ">" +
            id +
            " — " +
            (state.bundle.controls[id].title || "") +
            "</option>"
          );
        })
      )
      .join("");
    var params = (check.params || [])
      .map(function (param) {
        var value = sel.params[param.id] || (param.values && param.values[0]) || "";
        return (
          '<label class="field">' +
          Guide.escapeHtml(param.label) +
          ' <input data-param="' +
          check.rule_id +
          ":" +
          param.id +
          '" value="' +
          Guide.escapeHtml(value) +
          '"></label>'
        );
      })
      .join("");
    var mapping =
      '<details class="check-map"><summary>Change which control this maps to</summary><label class="field">Map to control <select data-control="' +
      check.rule_id +
      '">' +
      options +
      "</select></label>" +
      params +
      "</details>";
    card.innerHTML =
      '<div class="check-top"><label class="check-enable"><input type="checkbox" data-enable="' +
      check.rule_id +
      '"' +
      (sel.enabled ? " checked" : "") +
      "> " +
      Guide.escapeHtml(check.title) +
      '</label><span class="pill ' +
      check.check_type +
      '">' +
      Guide.termHtml(check.check_type, Guide.typeLabel(check.check_type)) +
      "</span></div><p class=\"check-reason\">" +
      Guide.escapeHtml(item.reason.text) +
      '</p><p class="note">' +
      Guide.escapeHtml(check.description) +
      "</p>" +
      mapping;
    bindCheckCard(card);
    return card;
  }

  function renderChecks() {
    var empty = document.getElementById("checks-empty");
    var usedBox = document.getElementById("checks-used");
    var unusedWrap = document.getElementById("checks-unused");
    var unusedList = document.getElementById("checks-unused-list");
    var summary = document.getElementById("checks-summary");
    usedBox.innerHTML = "";
    unusedList.innerHTML = "";
    if (!state.bundle) {
      empty.hidden = false;
      unusedWrap.hidden = true;
      summary.hidden = true;
      return;
    }
    empty.hidden = true;
    var classified = Guide.classifyLibraryChecks(
      library.checks || [],
      state.selected,
      state.bundle.controls,
      window.Enact.suggestControl
    );
    var mappingNote = "";
    if (state.checksDoc) {
      mappingNote =
        "Using " +
        (state.checksName || "checks.json") +
        (state.checksDoc["component-definition"] ? " (OSCAL Component Definition)" : "") +
        " from this tab. ";
    }
    summary.hidden = false;
    summary.textContent =
      mappingNote +
      classified.used.length +
      " checks apply to this catalog. " +
      classified.unused.length +
      " other library checks are unused.";
    classified.used.forEach(function (item) {
      usedBox.appendChild(renderCheckCard(item, false));
    });
    unusedWrap.hidden = classified.unused.length === 0;
    document.getElementById("checks-unused-summary").textContent =
      "Other library checks (" + classified.unused.length + ") — not used for this catalog";
    classified.unused.forEach(function (item) {
      unusedList.appendChild(renderCheckCard(item, true));
    });
  }

  function setEvidenceView(view) {
    evidenceView = view;
    var tableWrap = document.getElementById("evidence-table-wrap");
    var raw = document.getElementById("evidence-preview");
    var tableBtn = document.getElementById("evidence-view-table");
    var rawBtn = document.getElementById("evidence-view-raw");
    var showTable = view === "table";
    tableWrap.hidden = !showTable;
    raw.hidden = showTable;
    tableBtn.setAttribute("aria-selected", showTable ? "true" : "false");
    rawBtn.setAttribute("aria-selected", showTable ? "false" : "true");
  }

  function renderEvidence() {
    var empty = document.getElementById("evidence-empty");
    var board = document.getElementById("evidence-board");
    var preview = document.getElementById("evidence-preview");
    var name = document.getElementById("evidence-file-name");
    var table = document.getElementById("evidence-table");
    var help = document.getElementById("evidence-help");
    help.textContent = Guide.evidenceHelp(enabledChecks());
    if (!state.evidence) {
      empty.hidden = false;
      board.hidden = true;
      name.textContent = "No file yet";
      renderProgress();
      return;
    }
    empty.hidden = true;
    board.hidden = false;
    preview.textContent = JSON.stringify(state.evidence, null, 2);
    name.textContent = state.evidenceName || "evidence.json";
    var rows = Guide.evidenceRows(state.evidence, {
      libraryChecks: library.checks,
      selected: state.selected,
      controls: state.bundle ? state.bundle.controls : {},
    });
    table.innerHTML = "";
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        Guide.escapeHtml(row.label) +
        "<div class=\"note\"><code>" +
        Guide.escapeHtml(row.setting) +
        "</code></div></td><td>" +
        Guide.escapeHtml(row.value) +
        "</td><td>" +
        (row.limit == null ? "—" : Guide.escapeHtml(row.limit)) +
        '</td><td class="status-' +
        row.status +
        '">' +
        Guide.escapeHtml(row.statusLabel) +
        "</td>";
      table.appendChild(tr);
    });
    setEvidenceView(evidenceView);
    renderProgress();
  }

  function renderRun() {
    var empty = document.getElementById("run-empty");
    var results = document.getElementById("run-results");
    if (!state.result) {
      empty.hidden = false;
      results.hidden = true;
      return;
    }
    empty.hidden = true;
    results.hidden = false;
    var counts = state.result.counts;
    document.getElementById("count-pass").textContent = String(counts.pass);
    document.getElementById("count-fail").textContent = String(counts.fail + counts.error);
    document.getElementById("count-manual").textContent = String(counts.not_automated + counts.needs_evidence);
    document.getElementById("count-draft").textContent = String(counts.draft);
    var body = document.getElementById("result-rows");
    body.innerHTML = "";
    state.result.outcomes.forEach(function (outcome) {
      var guide = Guide.resultGuidance(outcome);
      var row = document.createElement("tr");
      row.innerHTML =
        "<td><code>" +
        Guide.escapeHtml(outcome.control_id) +
        "</code></td><td>" +
        Guide.escapeHtml(outcome.rule_id) +
        '</td><td><span class="pill ' +
        outcome.status +
        " " +
        (outcome.check_type || "") +
        '">' +
        Guide.escapeHtml(guide.label) +
        "</span></td><td>" +
        Guide.escapeHtml(outcome.message) +
        '</td><td class="next-step">' +
        Guide.escapeHtml(guide.next) +
        "</td>";
      body.appendChild(row);
    });
    document.getElementById("oscal-preview").textContent = JSON.stringify(state.result.oscal, null, 2);
  }

  function currentManifest() {
    if (state.checksDoc) {
      return state.checksDoc;
    }
    var ids = Object.keys(state.selected).filter(function (id) {
      return state.selected[id].enabled;
    });
    if (!ids.length) {
      throw new Error("Select at least one check.");
    }
    var manifest = window.Enact.manifestFromLibrary(library, state.bundle, ids);
    manifest.checks.forEach(function (check) {
      var sel = state.selected[check.rule_id];
      if (sel && sel.control_id) {
        check.control_id = sel.control_id;
      }
    });
    return manifest;
  }

  function downloadBlob(filename, text, type) {
    var blob = new Blob([text], { type: type || "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 0);
  }

  function runAssessment() {
    if (!policy) {
      showBanner("The policy engine is still loading.", "error");
      return;
    }
    if (!state.bundle) {
      showBanner("Open a catalog first, or use the bundled example.", "error");
      go("catalog");
      return;
    }
    var checks;
    try {
      checks = currentManifest();
    } catch (err) {
      showBanner(err.message, "error");
      go("checks");
      return;
    }
    var started = new Date();
    var startedIso = started.toISOString();
    setStatus("Evaluating in this tab…");
    window.Enact.runAssessment({
      catalog: state.catalog,
      checks: checks,
      evidence: state.evidence || {},
      policy: policy,
      library: library,
      title: (state.bundle.titles && state.bundle.titles[0]) || "Enact assessment",
      startedIso: startedIso,
      endedIso: new Date().toISOString(),
      inputLabel: state.evidenceName || "this-tab",
      reportAssets: { themeCss: themeCss, themeJs: themeJs },
    })
      .then(function (result) {
        state.result = result;
        renderRun();
        renderProgress();
        setStatus("Evaluated in this tab. Nothing was uploaded.", "ok");
        showBanner("");
        go("run");
      })
      .catch(function (err) {
        showBanner(err.message || String(err), "error");
        setStatus("Evaluation did not finish.", "error");
      });
  }

  document.querySelectorAll("[data-go]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      go(btn.getAttribute("data-go"));
    });
  });
  document.getElementById("use-example").addEventListener("click", useExample);
  document.getElementById("run-from-summary").addEventListener("click", runAssessment);
  document.getElementById("catalog-file").addEventListener("change", function (event) {
    readFile(event.target)
      .then(function (file) {
        if (file.data["component-definition"]) {
          throw new Error(
            "That is a Component Definition. Open a catalog here, then open the Component Definition on Checks."
          );
        }
        state.exampleLoaded = false;
        setCatalog(file.data, file.name);
      })
      .catch(function (err) {
        showBanner(err.message, "error");
      });
  });
  document.getElementById("checks-file").addEventListener("change", function (event) {
    readFile(event.target)
      .then(function (file) {
        var parsed = window.Enact.parseChecks(file.data);
        state.checksDoc = file.data;
        state.checksName = file.name;
        if (file.data["component-definition"] && state.catalog) {
          state.bundle = window.Enact.loadBundle([state.catalog, file.data]);
        }
        parsed.checks.forEach(function (check) {
          state.selected[check.rule_id] = {
            enabled: true,
            control_id: check.control_id,
            params: {},
          };
        });
        renderChecks();
        renderLoadSummary();
        renderProgress();
        showBanner("Loaded " + file.name + " in this tab.");
      })
      .catch(function (err) {
        showBanner(err.message, "error");
      });
  });
  document.getElementById("evidence-file").addEventListener("change", function (event) {
    readFile(event.target)
      .then(function (file) {
        state.evidence = file.data;
        state.evidenceName = file.name;
        renderEvidence();
        renderLoadSummary();
        showBanner("Loaded " + file.name + " in this tab. Nothing was uploaded.");
      })
      .catch(function (err) {
        showBanner(err.message, "error");
      });
  });
  document.getElementById("use-passing").addEventListener("click", function () {
    var sample = library.samples && library.samples["access-control"];
    if (!sample) {
      return;
    }
    state.evidence = sample.passing;
    state.evidenceName = "passing.json";
    renderEvidence();
    renderLoadSummary();
  });
  document.getElementById("use-failing").addEventListener("click", function () {
    var sample = library.samples && library.samples["access-control"];
    if (!sample) {
      return;
    }
    state.evidence = sample.failing;
    state.evidenceName = "failing.json";
    renderEvidence();
    renderLoadSummary();
  });
  document.getElementById("evidence-view-table").addEventListener("click", function () {
    setEvidenceView("table");
  });
  document.getElementById("evidence-view-raw").addEventListener("click", function () {
    setEvidenceView("raw");
  });
  document.getElementById("run-btn").addEventListener("click", runAssessment);
  document.getElementById("download-oscal").addEventListener("click", function () {
    if (!state.result) {
      return;
    }
    downloadBlob("assessment-results.json", JSON.stringify(state.result.oscal, null, 2) + "\n", "application/json");
  });
  document.getElementById("download-html").addEventListener("click", function () {
    if (!state.result) {
      return;
    }
    downloadBlob("summary.html", state.result.html, "text/html");
  });
  document.getElementById("download-poam").addEventListener("click", function () {
    if (!state.result) {
      return;
    }
    downloadBlob("poam.json", JSON.stringify(state.result.poam, null, 2) + "\n", "application/json");
  });

  setStatus("Loading vendored policy.wasm…");
  Promise.all([
    fetch("./policy.wasm", { cache: "no-store" }).then(function (res) {
      if (!res.ok) {
        throw new Error("Could not fetch policy.wasm from this origin.");
      }
      return res.arrayBuffer();
    }),
    fetch("./theme.css", { cache: "no-store" }).then(function (res) {
      return res.ok ? res.text() : "";
    }),
    fetch("./theme.js", { cache: "no-store" }).then(function (res) {
      return res.ok ? res.text() : "";
    }),
  ])
    .then(function (loaded) {
      themeCss = loaded[1];
      themeJs = loaded[2];
      return window.EnactOpa.loadPolicy(loaded[0]);
    })
    .then(function (loadedPolicy) {
      policy = loadedPolicy;
      setStatus("Ready. Catalogs and evidence stay in this tab.", "ok");
    })
    .catch(function (err) {
      setStatus(err.message || String(err), "error");
    });
})();
