/**
 * Plain-language helpers for the Enact in-browser walk-through.
 * No DOM. Used by site/app.js and tests/eval_guide.js.
 */
(function (root) {
  "use strict";

  var GLOSSARY = {
    OSCAL: "A standard way to write security controls as files so tools can share them.",
    "checks.json": "Enact's list of which check covers which control.",
    "Component Definition":
      "An OSCAL file that says which check implements which control. Same job as checks.json, in the standard OSCAL shape.",
    Rego: "The language used to write an automated check for OPA.",
    OPA: "Open Policy Agent — the engine that answers automated checks. This tab uses a copy of version 1.8.",
    "OPA 1.8.x":
      "Open Policy Agent 1.8 — the engine that answers automated checks. Enact vendors that version in this tab.",
    "POA&M": "Plan of Action and Milestones — the list of failed checks that still need a fix.",
    "poam.json": "The downloadable list of failed checks that still need a fix (a POA&M).",
    "assessment-results.json":
      "The official results file. Other GRC tools can read it because it uses the OSCAL standard.",
    Draft: "A check stub that has not been reviewed yet. Not a pass, not a failure, and not a POA&M item.",
    "Need evidence": "A person still has to confirm this. That is not a failure.",
    manual: "A check a person must confirm. Enact will not pass or fail it from the settings file.",
    automated: "A check Enact can answer from the settings file alone.",
    hybrid:
      "Enact can check the setting, but a person still has to sign off before it counts as done.",
    Catalog: "The list of controls you want to assess.",
    Evidence: "A settings file that describes how the system is configured right now.",
  };

  var FIELD_HINTS = {
    account_review_days: {
      rule_id: "ac-account-review",
      compare: "at_most",
      label: "Account review interval (days)",
    },
    lockout_threshold: {
      rule_id: "ac-login-lockout",
      compare: "at_most",
      label: "Failed-login lockout threshold",
    },
    privileged_review_days: {
      rule_id: "ac-privileged-review",
      compare: "at_most",
      label: "Privileged-account review interval (days)",
    },
    inactive_disable_days: {
      rule_id: "ac-inactive-disable",
      compare: "at_most",
      label: "Idle days before an unused account is disabled",
    },
    mfa_required: {
      rule_id: "ac-mfa-enforced",
      compare: "equals",
      label: "Multi-factor authentication required",
    },
    password_min_length: {
      rule_id: "ac-password-length",
      compare: "at_least",
      label: "Minimum password length",
    },
    retention_days: {
      rule_id: "au-log-retention",
      compare: "at_least",
      label: "How long audit logs are kept (days)",
    },
    audit_enabled: {
      rule_id: "au-logging-enabled",
      compare: "equals",
      label: "Audit logging turned on",
    },
    encryption_at_rest: {
      rule_id: "sc-encryption-at-rest",
      compare: "equals",
      label: "Stored data is encrypted",
    },
    tls_required: {
      rule_id: "sc-encryption-in-transit",
      compare: "equals",
      label: "Data in transit uses TLS",
    },
  };

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function glossaryTip(term) {
    return GLOSSARY[term] || "";
  }

  function termHtml(term, display) {
    var tip = glossaryTip(term);
    var label = display || term;
    if (!tip) {
      return escapeHtml(label);
    }
    return (
      '<span class="term" tabindex="0">' +
      escapeHtml(label) +
      '<span class="term__tip" role="tooltip">' +
      escapeHtml(tip) +
      "</span></span>"
    );
  }

  function typeLabel(checkType) {
    return (
      {
        automated: "Automated",
        manual: "Need evidence",
        hybrid: "Hybrid — setting + sign-off",
        draft: "Draft",
      }[checkType] || checkType || ""
    );
  }

  function statusLabel(status) {
    return (
      {
        pass: "Passed",
        fail: "Failed",
        not_automated: "Need evidence",
        needs_evidence: "Need evidence",
        error: "Failed",
        draft: "Draft",
      }[status] || status
    );
  }

  function flattenEvidence(value, prefix) {
    var rows = [];
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return rows;
    }
    Object.keys(value).forEach(function (key) {
      var path = prefix ? prefix + "." + key : key;
      var child = value[key];
      if (child && typeof child === "object" && !Array.isArray(child)) {
        rows = rows.concat(flattenEvidence(child, path));
      } else {
        rows.push({ setting: key, path: path, value: child });
      }
    });
    return rows;
  }

  function libraryById(libraryChecks) {
    var map = {};
    (libraryChecks || []).forEach(function (check) {
      map[check.rule_id] = check;
    });
    return map;
  }

  function hintForSetting(setting, libraryChecks) {
    if (FIELD_HINTS[setting]) {
      return FIELD_HINTS[setting];
    }
    var found = null;
    (libraryChecks || []).forEach(function (check) {
      (check.payload_requires || []).forEach(function (field) {
        if (field === setting) {
          found = {
            rule_id: check.rule_id,
            compare: "at_most",
            label: setting.replace(/_/g, " "),
          };
        }
      });
    });
    return found;
  }

  function firstParamValue(check, selected, control) {
    var param = (check && check.params && check.params[0]) || null;
    if (!param) {
      return null;
    }
    if (selected && selected.params && selected.params[param.id]) {
      return selected.params[param.id];
    }
    if (control && control.params) {
      var keys = Object.keys(control.params);
      if (keys.length) {
        return control.params[keys[0]];
      }
    }
    if (param.values && param.values[0]) {
      return param.values[0];
    }
    return null;
  }

  function compareStatus(value, limit, compare) {
    if (limit === null || limit === undefined || limit === "") {
      return { status: "no_limit", label: "No limit from the selected checks" };
    }
    if (compare === "at_most") {
      var atMost = Number(value) <= Number(limit);
      return { status: atMost ? "within" : "over", label: atMost ? "Within the limit" : "Over the limit" };
    }
    if (compare === "at_least") {
      var atLeast = Number(value) >= Number(limit);
      return {
        status: atLeast ? "within" : "over",
        label: atLeast ? "Meets the minimum" : "Below the minimum",
      };
    }
    if (compare === "equals") {
      var same = String(value).toLowerCase() === String(limit).toLowerCase();
      return { status: same ? "within" : "over", label: same ? "Matches" : "Does not match" };
    }
    return { status: "info", label: "Recorded" };
  }

  function evidenceRows(evidence, opts) {
    opts = opts || {};
    var libraryChecks = opts.libraryChecks || [];
    var selected = opts.selected || {};
    var controls = opts.controls || {};
    var byId = libraryById(libraryChecks);
    return flattenEvidence(evidence).map(function (row) {
      var hint = hintForSetting(row.setting, libraryChecks);
      var check = hint ? byId[hint.rule_id] : null;
      var sel = check ? selected[check.rule_id] : null;
      var control = sel && sel.control_id ? controls[sel.control_id] : null;
      var limit = check ? firstParamValue(check, sel, control) : null;
      var used = Boolean(check && sel && sel.enabled);
      var compared = used
        ? compareStatus(row.value, limit, hint && hint.compare)
        : { status: "unused", label: "Not used by a selected check" };
      if (used && check && check.check_type === "hybrid" && compared.status === "within") {
        compared = {
          status: "within",
          label: "Within the limit — still needs reviewer sign-off",
        };
      }
      return {
        setting: row.setting,
        path: row.path,
        label: (hint && hint.label) || row.setting.replace(/_/g, " "),
        value: row.value,
        limit: used ? limit : null,
        compare: hint && hint.compare,
        status: compared.status,
        statusLabel: compared.label,
        rule_id: check ? check.rule_id : "",
        used: used,
      };
    });
  }

  function evidenceHelp(enabledChecks) {
    var fields = [];
    (enabledChecks || []).forEach(function (check) {
      (check.payload_requires || []).forEach(function (field) {
        if (fields.indexOf(field) === -1) {
          fields.push(field);
        }
      });
      var template = check.input_template || {};
      Object.keys(template).forEach(function (group) {
        var inner = template[group];
        if (inner && typeof inner === "object") {
          Object.keys(inner).forEach(function (field) {
            if (fields.indexOf(field) === -1) {
              fields.push(field);
            }
          });
        }
      });
    });
    var lead =
      "For a real assessment, bring a JSON settings file from your identity system (an IAM export) or an Enact adapter.";
    if (!fields.length) {
      return lead + " The samples on this page are only for trying the walk-through.";
    }
    return (
      lead +
      " Include these settings: " +
      fields.join(", ") +
      ". The samples on this page are only for trying the walk-through."
    );
  }

  function matchReason(check, controlId, control) {
    if (!controlId || !control) {
      return {
        kind: "none",
        text: "This catalog has no control about this topic, so the check is unused.",
      };
    }
    var title = control.title || controlId;
    if (control.props && control.props["rule-id"] === check.rule_id) {
      return {
        kind: "rule-id",
        text:
          "Applies to " +
          controlId +
          " — this catalog already maps that control to this check (" +
          title +
          ").",
      };
    }
    return {
      kind: "mapped",
      text: "Mapped to " + controlId + " — " + title + ".",
    };
  }

  function classifyLibraryChecks(libraryChecks, selected, controls, suggestControl) {
    var used = [];
    var unused = [];
    (libraryChecks || []).forEach(function (check) {
      var sel = selected[check.rule_id] || { enabled: false, control_id: "", params: {} };
      var controlId = sel.control_id || "";
      var suggested =
        !controlId && typeof suggestControl === "function" ? suggestControl(check, controls) || "" : "";
      var resolvedId = controlId || suggested;
      var control = resolvedId ? controls[resolvedId] : null;
      var reason = matchReason(check, resolvedId, control);
      if (!sel.enabled && suggested && reason.kind !== "none") {
        reason = {
          kind: "suggested",
          text:
            "Could apply to " +
            suggested +
            " — " +
            ((control && control.title) || "") +
            ". Not selected for this run.",
        };
      }
      var item = {
        check: check,
        selected: sel,
        controlId: resolvedId,
        reason: reason,
        enabled: Boolean(sel.enabled),
      };
      if (item.enabled) {
        used.push(item);
      } else {
        unused.push(item);
      }
    });
    return { used: used, unused: unused };
  }

  function exampleLoadSummary(opts) {
    opts = opts || {};
    var controls = opts.controls || {};
    var selected = opts.selected || {};
    var libraryChecks = opts.libraryChecks || [];
    var enabled = libraryChecks.filter(function (check) {
      return selected[check.rule_id] && selected[check.rule_id].enabled;
    });
    var evidenceName = opts.evidenceName || "evidence.json";
    var failing = /fail/i.test(evidenceName);
    return {
      title: opts.title || "Example loaded — ready to run",
      controlCount: Object.keys(controls).length,
      checkCount: enabled.length,
      checkTitles: enabled.map(function (check) {
        return check.title;
      }),
      evidenceName: evidenceName,
      evidenceKind: failing ? "failing sample" : "passing sample",
      nextAction: "Run the assessment",
      nextHint: "Everything needed is in this tab. Run to see what passed and what still needs evidence.",
    };
  }

  function resultGuidance(outcome) {
    outcome = outcome || {};
    var status = outcome.status;
    var type = outcome.check_type;
    if (status === "pass") {
      return {
        label: "Passed",
        next: "No further action.",
      };
    }
    if (status === "fail") {
      return {
        label: "Failed",
        next: "Fix the setting, or add a POA&M item.",
      };
    }
    if (status === "error") {
      return {
        label: "Failed",
        next: "Fix the settings file or mapping, then run again.",
      };
    }
    if (status === "draft") {
      return {
        label: "Draft",
        next: "Review this stub in the CLI before trusting it.",
      };
    }
    if (status === "not_automated" || type === "manual") {
      return {
        label: "Need evidence",
        next: "Have a person confirm the paperwork.",
      };
    }
    if (status === "needs_evidence" || type === "hybrid") {
      return {
        label: "Need evidence",
        next: "A reviewer must sign off. Not Passed until then.",
      };
    }
    return { label: statusLabel(status), next: "See Why for this check." };
  }

  function collapseSecondary(step) {
    return step !== "catalog";
  }

  function oscalReadableSummary(opts) {
    opts = opts || {};
    var oscal = opts.oscal || {};
    var outcomes = opts.outcomes || [];
    var ar = oscal["assessment-results"] || {};
    var meta = ar.metadata || {};
    var result = (ar.results && ar.results[0]) || {};
    var observations = result.observations || [];
    var findings = result.findings || [];
    var counts = { pass: 0, fail: 0, needEvidence: 0, draft: 0 };
    var rows = outcomes.map(function (outcome) {
      var status = outcome.status || "";
      if (status === "pass") {
        counts.pass += 1;
      } else if (status === "fail" || status === "error") {
        counts.fail += 1;
      } else if (status === "draft") {
        counts.draft += 1;
      } else {
        counts.needEvidence += 1;
      }
      return {
        control: outcome.control_id || "",
        check: outcome.rule_id || "",
        status: status,
        label: statusLabel(status),
        why: outcome.message || "",
      };
    });
    var title = meta.title || "Assessment results";
    var oscalVersion = meta["oscal-version"] || "1.1.2";
    return {
      title: title,
      oscalVersion: oscalVersion,
      lastModified: meta["last-modified"] || "",
      observationCount: observations.length,
      findingCount: findings.length,
      counts: counts,
      rows: rows,
      lede:
        counts.pass +
        " passed, " +
        counts.fail +
        " failed, " +
        counts.needEvidence +
        " Need evidence, " +
        counts.draft +
        " Draft — " +
        observations.length +
        " observations in the OSCAL file.",
      facts: [
        { label: "Title", value: title },
        { label: "OSCAL version", value: oscalVersion },
        { label: "Observations", value: String(observations.length) },
        { label: "Findings", value: String(findings.length) },
      ],
    };
  }

  function progressFromState(state) {
    state = state || {};
    var controlCount = state.controls ? Object.keys(state.controls).length : 0;
    var selected = state.selected || {};
    var checkCount = Object.keys(selected).filter(function (id) {
      return selected[id] && selected[id].enabled;
    }).length;
    return {
      catalog: controlCount ? controlCount + " controls" : "Not yet",
      checks: checkCount ? checkCount + " selected" : "Not yet",
      evidence: state.evidenceName || "Not yet",
      run: state.hasResult ? "Done" : "Not yet",
    };
  }

  var api = {
    GLOSSARY: GLOSSARY,
    FIELD_HINTS: FIELD_HINTS,
    escapeHtml: escapeHtml,
    glossaryTip: glossaryTip,
    termHtml: termHtml,
    typeLabel: typeLabel,
    statusLabel: statusLabel,
    flattenEvidence: flattenEvidence,
    evidenceRows: evidenceRows,
    evidenceHelp: evidenceHelp,
    matchReason: matchReason,
    classifyLibraryChecks: classifyLibraryChecks,
    exampleLoadSummary: exampleLoadSummary,
    resultGuidance: resultGuidance,
    progressFromState: progressFromState,
    collapseSecondary: collapseSecondary,
    oscalReadableSummary: oscalReadableSummary,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.EnactGuide = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
