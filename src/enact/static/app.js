(() => {
  const state = {
    step: "catalog",
    catalog: null,
    inspect: null,
    library: [],
    suggestions: {},
    selected: {},
    input: null,
    result: null,
  };

  const $ = (id) => document.getElementById(id);
  const steps = ["catalog", "checks", "evidence", "run"];

  function showBanner(message) {
    const el = $("banner");
    el.hidden = !message;
    el.textContent = message || "";
  }

  function go(step) {
    state.step = step;
    steps.forEach((name) => {
      $(`step-${name}`).hidden = name !== step;
    });
    document.querySelectorAll(".stepper button").forEach((btn) => {
      btn.setAttribute("aria-current", btn.dataset.go === step ? "step" : "false");
    });
    if (step === "checks") renderChecks();
    if (step === "evidence") renderEvidence();
  }

  function setCli(payload) {
    if (!payload) return;
    $("cli-summary").textContent = payload.summary || "";
    $("cli-command").textContent = payload.command || "";
    const flags = $("cli-flags");
    flags.innerHTML = "";
    (payload.flags || []).forEach((item) => {
      const li = document.createElement("li");
      li.innerHTML = `<code>${escapeHtml(item.flag)}</code> — ${escapeHtml(item.text)}`;
      flags.appendChild(li);
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function api(path, options) {
    showBanner("");
    const response = await fetch(path, options);
    const type = response.headers.get("content-type") || "";
    if (type.includes("application/zip")) {
      if (!response.ok) throw new Error("Could not build the project zip.");
      return response.blob();
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong. Try again.");
    return data;
  }

  async function loadLibrary() {
    const data = await api("/api/library");
    state.library = data.checks || [];
  }

  async function loadExample() {
    const data = await api("/api/example");
    applyInspect(data, data.catalog);
  }

  async function inspectUpload(file) {
    const text = await file.text();
    let catalog;
    try {
      catalog = JSON.parse(text);
    } catch {
      throw new Error("That file is not valid JSON. Export OSCAL JSON from Codify, or pick the example.");
    }
    const data = await api("/api/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ catalog }),
    });
    applyInspect(data, catalog);
  }

  async function applyInspect(data, catalog) {
    state.catalog = catalog;
    state.inspect = data;
    $("catalog-empty").hidden = true;
    $("catalog-summary").hidden = false;
    $("catalog-title").textContent = data.title;
    $("catalog-meta").textContent = `${data.kind} · ${data.controls.length} controls`;
    const list = $("catalog-controls");
    list.innerHTML = "";
    data.controls.forEach((control) => {
      const li = document.createElement("li");
      li.innerHTML = `<code>${escapeHtml(control.id)}</code> — ${escapeHtml(control.title)}`;
      list.appendChild(li);
    });
    const suggest = await api("/api/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ catalog }),
    });
    state.suggestions = suggest.suggestions || {};
    preselectMatches();
    setCli(data.cli || suggest.cli);
  }

  function preselectMatches() {
    state.library.forEach((check) => {
      const match = state.suggestions[check.rule_id];
      if (!match) return;
      if (!state.selected[check.rule_id]) {
        state.selected[check.rule_id] = selectionFrom(check, match);
      }
    });
  }

  function selectionFrom(check, controlId) {
    const control = (state.inspect?.controls || []).find((item) => item.id === controlId);
    const params = {};
    (check.params || []).forEach((param) => {
      params[param.id] = (param.values && param.values[0]) || "";
    });
    if (control) {
      (control.params || []).forEach((param, index) => {
        params[param.id] = param.value;
        const libraryParam = (check.params || [])[index];
        if (libraryParam && param.value) params[libraryParam.id] = param.value;
      });
    }
    return {
      rule_id: check.rule_id,
      control_id: controlId,
      params,
      policy: check.policy || "",
    };
  }

  function renderChecks() {
    const host = $("check-list");
    const empty = $("checks-empty");
    host.innerHTML = "";
    if (!state.catalog) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    const controls = state.inspect?.controls || [];
    state.library.forEach((check) => {
      const selected = Boolean(state.selected[check.rule_id]);
      const current = state.selected[check.rule_id] || selectionFrom(check, state.suggestions[check.rule_id] || "");
      const card = document.createElement("article");
      card.className = "check";
      const options = ['<option value="">Choose a control…</option>']
        .concat(
          controls.map((control) => {
            const chosen = current.control_id === control.id ? " selected" : "";
            return `<option value="${escapeHtml(control.id)}"${chosen}>${escapeHtml(control.id)} — ${escapeHtml(control.title)}</option>`;
          })
        )
        .join("");
      const paramFields = (check.params || [])
        .map((param) => {
          const value = current.params[param.id] || "";
          return `<label class="field">${escapeHtml(param.label)}
            <input data-param="${escapeHtml(check.rule_id)}" data-key="${escapeHtml(param.id)}" value="${escapeHtml(value)}"></label>`;
        })
        .join("");
      const extraParams = Object.entries(current.params)
        .filter(([key]) => !(check.params || []).some((param) => param.id === key))
        .map(([key, value]) => `<label class="field">${escapeHtml(key)} (from catalog)
          <input data-param="${escapeHtml(check.rule_id)}" data-key="${escapeHtml(key)}" value="${escapeHtml(value)}"></label>`)
        .join("");
      card.innerHTML = `
        <div class="check-top">
          <label><input type="checkbox" data-select="${escapeHtml(check.rule_id)}" ${selected ? "checked" : ""}>
            <strong>${escapeHtml(check.title)}</strong></label>
          <span class="pill ${escapeHtml(check.check_type)}">${escapeHtml(check.check_type)}</span>
        </div>
        <p>${escapeHtml(check.description)}</p>
        <label class="field">Map to control
          <select data-control="${escapeHtml(check.rule_id)}">${options}</select>
        </label>
        ${paramFields}${extraParams}
        ${
          check.policy
            ? `<details class="advanced"><summary>Advanced: view or edit the Rego</summary>
               <label class="field">Rego policy
               <textarea data-policy="${escapeHtml(check.rule_id)}">${escapeHtml(current.policy || "")}</textarea></label></details>`
            : `<p class="note">Manual check — Enact will record this as needing a person, not as a failure.</p>`
        }
      `;
      host.appendChild(card);
    });
    host.querySelectorAll("[data-select]").forEach((box) => {
      box.addEventListener("change", () => toggleCheck(box.dataset.select, box.checked));
    });
    host.querySelectorAll("[data-control]").forEach((select) => {
      select.addEventListener("change", () => updateSelection(select.dataset.control, { control_id: select.value }));
    });
    host.querySelectorAll("[data-param]").forEach((input) => {
      input.addEventListener("input", () => {
        const current = state.selected[input.dataset.param] || selectionFrom(findCheck(input.dataset.param), "");
        current.params[input.dataset.key] = input.value;
        state.selected[input.dataset.param] = current;
      });
    });
    host.querySelectorAll("[data-policy]").forEach((area) => {
      area.addEventListener("input", () => updateSelection(area.dataset.policy, { policy: area.value }));
    });
    const ids = Object.keys(state.selected);
    setCli({
      command: ids.length
        ? `enact init ${ids.map((id) => `--check ${id}`).join(" ")} --out my-project`
        : "enact checks list",
      summary: ids.length
        ? "These flags write a manifest and copy the Rego files into a folder."
        : "Tick a check to see the init command.",
      flags: [
        { flag: "enact checks list", text: "Shows every library check with a one-line description." },
        { flag: "--check", text: "Include this library check in the project." },
        { flag: "--out", text: "Folder for manifest.json, policies/, and a sample input." },
      ],
    });
  }

  function findCheck(ruleId) {
    return state.library.find((item) => item.rule_id === ruleId);
  }

  function toggleCheck(ruleId, on) {
    const check = findCheck(ruleId);
    if (!check) return;
    if (on) {
      const match = state.suggestions[ruleId] || "";
      state.selected[ruleId] = state.selected[ruleId] || selectionFrom(check, match);
    } else {
      delete state.selected[ruleId];
    }
    renderChecks();
  }

  function updateSelection(ruleId, patch) {
    const check = findCheck(ruleId);
    const current = state.selected[ruleId] || selectionFrom(check, state.suggestions[ruleId] || "");
    state.selected[ruleId] = { ...current, ...patch, params: { ...current.params, ...(patch.params || {}) } };
  }

  function selectedPayload() {
    return Object.values(state.selected).filter((item) => item.control_id);
  }

  function renderEvidence() {
    const has = Boolean(state.input);
    $("evidence-empty").hidden = has;
    $("evidence-preview").hidden = !has;
    if (has) $("evidence-preview").textContent = JSON.stringify(state.input, null, 2);
    setCli({
      command: "enact run --input inputs/sample.json --workdir .",
      summary: has
        ? "Your uploaded JSON will be passed as --input."
        : "If you skip the upload, Enact uses the passing samples from the library.",
      flags: [
        { flag: "--input", text: "JSON config exported from the system under assessment." },
        { flag: "--workdir", text: "Folder that holds the policy files named in the manifest." },
      ],
    });
  }

  function downloadBlob(filename, blob, type) {
    const url = URL.createObjectURL(new Blob([blob], { type }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function templateForSelection() {
    const docs = selectedPayload()
      .map((item) => findCheck(item.rule_id))
      .filter(Boolean)
      .map((check) => check.input_template || check.passing || {});
    if (!docs.length) return { iam: {}, logging: {}, crypto: {} };
    return docs.reduce((acc, doc) => {
      Object.keys(doc).forEach((key) => {
        if (doc[key] && typeof doc[key] === "object" && !Array.isArray(doc[key])) {
          acc[key] = { ...(acc[key] || {}), ...doc[key] };
        } else {
          acc[key] = doc[key];
        }
      });
      return acc;
    }, {});
  }

  async function runAssessment() {
    if (!state.catalog) throw new Error("Load a catalog first.");
    const selections = selectedPayload();
    if (!selections.length) throw new Error("Choose at least one check and map it to a control.");
    const data = await api("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        catalog: state.catalog,
        selections,
        input: state.input,
        title: "Guided Enact run",
      }),
    });
    state.result = data;
    $("run-empty").hidden = true;
    $("run-results").hidden = false;
    $("download-project").hidden = false;
    $("report-frame").srcdoc = data.html;
    const box = $("run-downloads");
    box.innerHTML = "";
    [
      ["assessment-results.json", JSON.stringify(data.assessment_results, null, 2), "application/json"],
      ["poam.json", JSON.stringify(data.poam, null, 2), "application/json"],
      ["summary.md", data.markdown, "text/markdown"],
      ["manifest.json", JSON.stringify(data.manifest, null, 2), "application/json"],
    ].forEach(([name, body, type]) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--ghost";
      btn.textContent = `Download ${name}`;
      btn.addEventListener("click", () => downloadBlob(name, body, type));
      box.appendChild(btn);
    });
    setCli(data.cli);
  }

  async function downloadProject() {
    const selections = selectedPayload();
    const blob = await api("/api/project", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        catalog: state.catalog,
        selections,
        input: state.input,
        title: "Guided Enact run",
      }),
    });
    downloadBlob("enact-project.zip", blob, "application/zip");
  }

  $("use-example").addEventListener("click", () => {
    loadExample().catch((err) => showBanner(err.message));
  });
  $("catalog-file").addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    if (file) inspectUpload(file).catch((err) => showBanner(err.message));
  });
  $("download-template").addEventListener("click", () => {
    downloadBlob("enact-input-template.json", JSON.stringify(templateForSelection(), null, 2), "application/json");
  });
  $("evidence-file").addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    try {
      state.input = JSON.parse(await file.text());
      if (!state.input || typeof state.input !== "object") throw new Error("bad");
      renderEvidence();
    } catch {
      showBanner("That evidence file must be a JSON object. Download the template if you need a starting point.");
    }
  });
  $("run-btn").addEventListener("click", () => {
    runAssessment().catch((err) => showBanner(err.message));
  });
  $("download-project").addEventListener("click", () => {
    downloadProject().catch((err) => showBanner(err.message));
  });
  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => go(btn.dataset.go));
  });
  $("cli-toggle").addEventListener("click", () => {
    const open = $("cli-body").hidden;
    $("cli-body").hidden = !open;
    $("cli-toggle").setAttribute("aria-expanded", String(open));
  });
  $("cli-copy").addEventListener("click", async () => {
    const text = $("cli-command").textContent || "";
    try {
      await navigator.clipboard.writeText(text);
      $("cli-copy").textContent = "Copied";
      setTimeout(() => {
        $("cli-copy").textContent = "Copy command";
      }, 1200);
    } catch {
      showBanner("Copy is unavailable in this browser. Select the command and copy it yourself.");
    }
  });

  setCli({
    command: "enact ui --port 43174",
    summary: "You are already in the guided app. The panel below will show the CLI for each step.",
    flags: [{ flag: "--port", text: "Local port. The server only listens on 127.0.0.1." }],
  });
  loadLibrary().catch((err) => showBanner(err.message));
})();
