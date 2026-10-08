/**
 * In-browser Enact runner: catalog inspect, evidence bind, OPA WASM evaluate,
 * OSCAL assessment-results / POA&M, and a self-contained HTML report.
 *
 * Same contract as enact run / OpaEngine (Rego v1, result.passed / message).
 * Custom / draft Rego is not compiled here — use the Enact CLI.
 */
(function (root) {
  "use strict";

  var VERSION = "0.1.0";
  var NS = "https://grcengineering.club/ns/enact";
  var CODIFY_NS = "https://grcengineering.club/ns/codify";
  var C2P_NS = "http://oscal-compass.github.io/compliance-trestle/schemas/oscal/cd/ibmcloud";
  var PVP_TITLE = "OPA";
  var OSCAL_VERSION = "1.1.2";
  var UUID_NS = "d4c6f1e2-7a91-4b33-9c0e-3e8f2a1b5d70";
  var PACKAGE_RE = /^\s*package\s+([A-Za-z_][\w.]*)/m;

  var PROP_ALIASES = {
    "rule-id": "rule-id",
    rule_id: "rule-id",
    Rule_Id: "rule-id",
    "check-id": "rule-id",
    Check_Id: "rule-id",
    "check-type": "check-type",
    check_type: "check-type",
    engine: "engine",
    "policy-path": "policy-path",
    policy_path: "policy-path",
    policy: "policy-path",
    query: "query",
    "ksi-id": "ksi-id",
    ksi_id: "ksi-id",
    KSI_Id: "ksi-id",
    "evidence-needed": "evidence-needed",
    evidence_needed: "evidence-needed",
  };

  var HTML_STATUS = {
    pass: "Passed",
    fail: "Failed",
    not_automated: "Manual",
    needs_evidence: "Not checked",
    error: "Failed",
    draft: "Draft",
  };

  var REPORT_CSS =
    "* { box-sizing: border-box; }" +
    "html { -webkit-text-size-adjust: 100%; }" +
    "body { margin: 0; min-height: 100vh; font: 15px/1.5 var(--font); background: var(--bg); color: var(--ink); }" +
    "a { color: var(--accent); }" +
    ".wrap { max-width: var(--max); margin: 0 auto; padding: 1.5rem 1.25rem 2.5rem; }" +
    ".kicker { margin: 0 0 .35rem; font-size: .75rem; font-weight: 650; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }" +
    "h1 { margin: 0 0 .45rem; font-size: 1.7rem; letter-spacing: -.02em; }" +
    ".lede { margin: 0 0 1.25rem; color: var(--muted); max-width: 46rem; }" +
    ".report-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: .8rem; align-items: flex-start; margin-bottom: .35rem; }" +
    ".cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .85rem; margin: 0 0 1.35rem; }" +
    ".card { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem 1.1rem 1.05rem; }" +
    ".card-top { display: flex; align-items: center; justify-content: space-between; gap: .6rem; margin-bottom: .35rem; }" +
    ".card-top .label { color: var(--muted); font-size: .92rem; }" +
    ".count { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: -.03em; }" +
    ".hint { margin: .45rem 0 0; color: var(--muted); font-size: .85rem; }" +
    ".pill { display: inline-flex; align-items: center; gap: .3rem; padding: .15rem .55rem; border-radius: 999px; font-size: .75rem; font-weight: 650; }" +
    ".pill.pass { background: var(--pass-bg); color: var(--pass); }" +
    ".pill.fail, .pill.error { background: var(--fail-bg); color: var(--fail); }" +
    ".pill.not_automated, .pill.needs_evidence, .pill.wait { background: var(--wait-bg); color: var(--wait); }" +
    ".pill.draft { background: var(--draft-bg); color: var(--draft); }" +
    ".bar { margin-top: .7rem; height: 8px; border-radius: 999px; background: var(--track); overflow: hidden; }" +
    ".bar > span { display: block; height: 100%; background: var(--accent); border-radius: inherit; }" +
    ".toolbar { display: flex; flex-wrap: wrap; gap: .65rem; align-items: center; justify-content: space-between; margin: 0 0 .75rem; }" +
    "#q { flex: 1 1 16rem; min-width: 12rem; border: 1px solid var(--line); border-radius: 10px; padding: .55rem .75rem; font: inherit; background: var(--card); color: var(--ink); }" +
    ".filters { display: flex; flex-wrap: wrap; gap: .35rem; }" +
    ".filters button { appearance: none; font: 650 13px var(--font); color: var(--muted); background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: .35rem .75rem; cursor: pointer; }" +
    '.filters button[aria-pressed="true"] { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }' +
    ".table-wrap { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); overflow: auto; }" +
    "table { width: 100%; border-collapse: collapse; }" +
    "th, td { text-align: left; padding: .75rem .85rem; border-bottom: 1px solid var(--line); }" +
    "th { font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); font-weight: 650; background: var(--table-head); }" +
    "code { font-family: var(--mono); font-size: .86em; }" +
    ".type { color: var(--muted); font-size: .85rem; text-transform: capitalize; }" +
    ".expand { appearance: none; width: 1.5rem; height: 1.5rem; margin-right: .4rem; border: 1px solid var(--line); border-radius: 6px; background: var(--ghost); color: var(--ink); cursor: pointer; vertical-align: middle; font-size: .75rem; }" +
    ".finding td { background: var(--table-head); padding: .4rem .85rem 1rem; }" +
    ".finding-list { display: grid; gap: .55rem; }" +
    ".finding-item { display: flex; gap: .7rem; align-items: flex-start; background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: .7rem .8rem; }" +
    ".dot { width: .7rem; height: .7rem; border-radius: 999px; margin-top: .35rem; background: var(--line); flex: none; }" +
    ".dot.fail { background: var(--fail); }" +
    ".finding-item h3 { margin: 0 0 .15rem; font-size: .92rem; }" +
    ".finding-item p { margin: 0; color: var(--muted); }" +
    ".empty { padding: 1.1rem .85rem; color: var(--muted); }" +
    "footer.note { margin-top: 1.2rem; color: var(--muted); font-size: .88rem; }" +
    "@media (max-width: 800px) { .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }" +
    "@media (max-width: 560px) { .cards { grid-template-columns: 1fr; } }";

  var REPORT_JS =
    "(function(){var search=document.getElementById('q');var chips=document.querySelectorAll('[data-filter]');var rows=document.querySelectorAll('tr.check');var empty=document.getElementById('empty');var filter='all';function matches(status){if(filter==='all')return true;if(filter==='pass')return status==='pass';if(filter==='fail')return status==='fail'||status==='error';if(filter==='manual')return status==='not_automated'||status==='needs_evidence';if(filter==='draft')return status==='draft';return status===filter;}function apply(){var q=(search&&search.value||'').trim().toLowerCase();var visible=0;rows.forEach(function(row){var status=row.getAttribute('data-status')||'';var hay=row.getAttribute('data-search')||'';var show=matches(status)&&(!q||hay.indexOf(q)!==-1);row.hidden=!show;var detail=row.nextElementSibling;if(detail&&detail.classList.contains('finding')&&!show){detail.hidden=true;}if(show)visible+=1;});if(empty)empty.hidden=visible!==0;}chips.forEach(function(chip){chip.addEventListener('click',function(){filter=chip.getAttribute('data-filter')||'all';chips.forEach(function(c){c.setAttribute('aria-pressed',String(c===chip));});apply();});});if(search)search.addEventListener('input',apply);document.querySelectorAll('[data-expand]').forEach(function(btn){btn.addEventListener('click',function(){var row=btn.closest('tr');if(!row)return;var detail=row.nextElementSibling;if(!detail||!detail.classList.contains('finding'))return;var open=detail.hidden;detail.hidden=!open;btn.setAttribute('aria-expanded',String(open));});});})();";

  var THEME_BOOTSTRAP =
    '(function(){var k="enact-theme",m="system";try{var s=localStorage.getItem(k);if(s==="light"||s==="dark"||s==="system")m=s;}catch(e){}var d=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches;var t=m==="dark"||(m!=="light"&&d)?"dark":"light";var r=document.documentElement;r.setAttribute("data-theme",t);r.setAttribute("data-theme-mode",m);r.style.colorScheme=t;})();';

  function evidenceError(message) {
    var text = String(message || "");
    if (text.indexOf("evidence:") !== 0) {
      text = "evidence: " + text;
    }
    var err = new Error(text);
    err.name = "EvidenceError";
    return err;
  }

  function getSubtle() {
    if (typeof crypto !== "undefined" && crypto.subtle) {
      return crypto.subtle;
    }
    try {
      return require("crypto").webcrypto.subtle;
    } catch (err) {
      throw new Error("Web Crypto is required to write OSCAL UUIDs");
    }
  }

  function utf8(text) {
    return new TextEncoder().encode(text);
  }

  function hex(bytes) {
    var out = "";
    for (var i = 0; i < bytes.length; i += 1) {
      out += bytes[i].toString(16).padStart(2, "0");
    }
    return out;
  }

  function uuidToBytes(value) {
    var hexStr = String(value).replace(/-/g, "");
    var bytes = new Uint8Array(16);
    for (var i = 0; i < 16; i += 1) {
      bytes[i] = parseInt(hexStr.slice(i * 2, i * 2 + 2), 16);
    }
    return bytes;
  }

  function bytesToUuid(bytes) {
    var h = hex(bytes);
    return (
      h.slice(0, 8) +
      "-" +
      h.slice(8, 12) +
      "-" +
      h.slice(12, 16) +
      "-" +
      h.slice(16, 20) +
      "-" +
      h.slice(20)
    );
  }

  function concatBytes(a, b) {
    var out = new Uint8Array(a.length + b.length);
    out.set(a, 0);
    out.set(b, a.length);
    return out;
  }

  function sha1Bytes(bytes) {
    return getSubtle().digest("SHA-1", bytes).then(function (buf) {
      return new Uint8Array(buf);
    });
  }

  function sha256Hex(text) {
    return getSubtle().digest("SHA-256", utf8(text)).then(function (buf) {
      return hex(new Uint8Array(buf));
    });
  }

  function uuid5(name) {
    var nsBytes = uuidToBytes(UUID_NS);
    return sha1Bytes(concatBytes(nsBytes, utf8(name))).then(function (digest) {
      var bytes = digest.subarray(0, 16);
      bytes[6] = (bytes[6] & 0x0f) | 0x50;
      bytes[8] = (bytes[8] & 0x3f) | 0x80;
      return bytesToUuid(bytes);
    });
  }

  function makeUuid() {
    var parts = Array.prototype.slice.call(arguments);
    return uuid5(parts.join("|"));
  }

  function nowIso(iso) {
    return String(iso).replace(/\.\d+/, "").replace("+00:00", "Z");
  }

  function canonicalJson(value) {
    if (value === null || typeof value !== "object") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return "[" + value.map(canonicalJson).join(",") + "]";
    }
    var keys = Object.keys(value).sort();
    var bits = keys.map(function (key) {
      return JSON.stringify(key) + ":" + canonicalJson(value[key]);
    });
    return "{" + bits.join(",") + "}";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeControlId(value) {
    var text = String(value || "")
      .trim()
      .replace(/\(([^)]+)\)/g, ".$1")
      .toLowerCase()
      .replace(/_/g, "-")
      .replace(/[^a-z0-9._-]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .replace(/\./g, "-")
      .replace(/^c-/, "");
    return text || "control";
  }

  function walkControls(node, visit) {
    (node.controls || []).forEach(function (control) {
      visit(control);
      walkControls(control, visit);
    });
    (node.groups || []).forEach(function (group) {
      walkControls(group, visit);
    });
  }

  function flattenPart(part) {
    var own = part.prose || "";
    var nested = (part.parts || []).map(flattenPart);
    return [own].concat(nested).filter(Boolean).join(" ").trim();
  }

  function partText(control, name) {
    var chunks = [];
    (control.parts || []).forEach(function (part) {
      if (part.name === name) {
        chunks.push(flattenPart(part));
      }
    });
    return chunks.filter(Boolean).join(" ").trim();
  }

  function statementId(control) {
    var parts = control.parts || [];
    for (var i = 0; i < parts.length; i += 1) {
      if (parts[i].name === "statement" && parts[i].id) {
        return String(parts[i].id);
      }
    }
    return control.id ? String(control.id) + "_smt" : null;
  }

  function paramValue(param) {
    var values = param.values || [];
    if (values.length) {
      return String(values[0]);
    }
    var select = param.select || {};
    var choices = select.choice || [];
    if (choices.length) {
      return String(choices[0]);
    }
    return null;
  }

  function propsMap(item) {
    var chosen = {};
    (item.props || []).forEach(function (prop) {
      if (!prop || !prop.name || prop.value === undefined || prop.value === null) {
        return;
      }
      var key = PROP_ALIASES[prop.name] || prop.name;
      var rank = 2;
      if (prop.ns === NS) {
        rank = 0;
      } else if (prop.ns === CODIFY_NS) {
        rank = 1;
      } else if (prop.ns) {
        rank = 3;
      }
      var previous = chosen[key];
      if (!previous || rank < previous[0]) {
        chosen[key] = [rank, String(prop.value)];
      }
    });
    var out = {};
    Object.keys(chosen).forEach(function (key) {
      out[key] = chosen[key][1];
    });
    return out;
  }

  function isValidationComponent(component) {
    return String((component && component.type) || "").toLowerCase() === "validation";
  }

  function groupPropsByRemarks(item) {
    var grouped = {};
    var order = [];
    ((item && item.props) || []).forEach(function (prop) {
      if (!prop || !prop.name || prop.value === undefined || prop.value === null) {
        return;
      }
      var remarks = String(prop.remarks || "");
      if (!grouped[remarks]) {
        grouped[remarks] = {};
        order.push(remarks);
      }
      grouped[remarks][String(prop.name)] = String(prop.value);
    });
    return order.map(function (key) {
      return grouped[key];
    });
  }

  function firstNamed(group, names) {
    var i;
    for (i = 0; i < names.length; i += 1) {
      if (group[names[i]]) {
        return group[names[i]];
      }
    }
    return null;
  }

  function collectNamed(props, names) {
    var found = [];
    (props || []).forEach(function (prop) {
      if (prop && names.indexOf(prop.name) !== -1 && prop.value) {
        found.push(String(prop.value));
      }
    });
    return found;
  }

  function csvList(value) {
    if (!value) {
      return [];
    }
    return String(value)
      .split(",")
      .map(function (part) {
        return part.trim();
      })
      .filter(Boolean);
  }

  function enactFields(group) {
    var map = {
      "check-type": "check-type",
      check_type: "check-type",
      engine: "engine",
      "policy-path": "policy-path",
      policy_path: "policy-path",
      policy: "policy-path",
      query: "query",
      "ksi-id": "ksi-id",
      ksi_id: "ksi-id",
      KSI_Id: "ksi-id",
      "evidence-needed": "evidence-needed",
      evidence_needed: "evidence-needed",
      evidence: "evidence",
      "payload-type": "payload-type",
      payload_type: "payload-type",
      "payload-versions": "payload-versions",
      payload_versions: "payload-versions",
      "payload-requires": "payload-requires",
      payload_requires: "payload-requires",
    };
    var fields = {};
    Object.keys(group || {}).forEach(function (name) {
      if (map[name]) {
        fields[map[name]] = group[name];
      }
    });
    return fields;
  }

  function uniqueIds(ids) {
    var out = [];
    (ids || []).forEach(function (id) {
      if (id && out.indexOf(id) === -1) {
        out.push(id);
      }
    });
    return out;
  }

  function ingestComponentDefinition(bundle, cdef) {
    var meta = cdef.metadata || {};
    if (meta.title) {
      bundle.titles.push(String(meta.title));
    }
    bundle.componentDefinitions.push(cdef);
    (cdef.components || []).forEach(function (component) {
      (component["control-implementations"] || []).forEach(function (implementation) {
        (implementation["set-parameters"] || []).forEach(function (param) {
          if (param["param-id"] && param.values && param.values.length) {
            bundle.params[String(param["param-id"])] = String(param.values[0]);
          }
        });
        (implementation["implemented-requirements"] || []).forEach(function (req) {
          var controlId = req["control-id"];
          if (!controlId || String(controlId).toLowerCase() === "na") {
            return;
          }
          controlId = String(controlId);
          var record = bundle.controls[controlId] || {
            control_id: controlId,
            title: "",
            statement: "",
            statement_id: null,
            params: {},
            param_labels: {},
            props: {},
          };
          var merged = {};
          Object.keys(record.props || {}).forEach(function (key) {
            merged[key] = record.props[key];
          });
          Object.keys(propsMap(implementation)).forEach(function (key) {
            merged[key] = propsMap(implementation)[key];
          });
          Object.keys(propsMap(req)).forEach(function (key) {
            merged[key] = propsMap(req)[key];
          });
          record.props = merged;
          (req["set-parameters"] || []).forEach(function (param) {
            if (param["param-id"] && param.values && param.values.length) {
              record.params[String(param["param-id"])] = String(param.values[0]);
              bundle.params[String(param["param-id"])] = String(param.values[0]);
            }
          });
          Object.keys(bundle.params).forEach(function (pid) {
            if (pid.indexOf(controlId + "_") === 0 || record.params[pid]) {
              if (!record.params[pid]) {
                record.params[pid] = bundle.params[pid];
              }
            }
          });
          if (!record.title) {
            record.title = String(component.title || controlId);
          }
          bundle.controls[controlId] = record;
        });
      });
    });
  }

  function preferValidation(components) {
    var validation = (components || []).filter(isValidationComponent);
    var opa = validation.filter(function (comp) {
      return String(comp.title || "").toUpperCase() === PVP_TITLE;
    });
    return opa.length ? opa : validation;
  }

  function specFromGroups(ruleId, controlId, ruleSet, irProps, implProps, paramIds, titleFallback, descriptionFallback) {
    var enact = Object.assign({}, enactFields(implProps), enactFields(irProps), enactFields(ruleSet));
    var checkId = firstNamed(ruleSet, ["Check_Id", "check-id", "check_id"]) || ruleId;
    var policy = enact["policy-path"] || null;
    if (!policy && String(checkId).slice(-5) === ".rego") {
      policy = checkId;
    }
    var checkType = enact["check-type"] || "automated";
    return {
      rule_id: ruleId,
      control_id: controlId,
      check_type: checkType,
      engine: enact.engine || (checkType === "manual" ? "none" : "opa"),
      policy: policy,
      query: enact.query || null,
      params: uniqueIds(paramIds),
      ksi_id: enact["ksi-id"] || null,
      title: firstNamed(ruleSet, ["Check_Description", "Rule_Description"]) || irProps.title || titleFallback,
      description: firstNamed(ruleSet, ["Rule_Description", "Check_Description"]) || descriptionFallback || null,
      evidence: enact.evidence || null,
      evidence_needed: enact["evidence-needed"] || null,
      payload_type: enact["payload-type"] || null,
      payload_versions: csvList(enact["payload-versions"]),
      payload_requires: csvList(enact["payload-requires"]),
      check_id: checkId !== ruleId ? checkId : null,
    };
  }

  function manifestFromComponentDefinition(cdef, source) {
    var components = (cdef && cdef.components) || [];
    if (!components.length) {
      throw new Error("component-definition has no components");
    }
    var ruleSets = {};
    preferValidation(components).forEach(function (comp) {
      groupPropsByRemarks(comp).forEach(function (group) {
        var ruleId = firstNamed(group, ["Rule_Id", "rule-id", "rule_id"]);
        if (ruleId) {
          ruleSets[ruleId] = group;
        }
      });
    });
    var paramsByRule = {};
    var service = components.filter(function (comp) {
      return !isValidationComponent(comp);
    });
    service.forEach(function (comp) {
      groupPropsByRemarks(comp).forEach(function (group) {
        var ruleId = firstNamed(group, ["Rule_Id", "rule-id", "rule_id"]);
        var paramId = group.Parameter_Id || group["parameter-id"];
        if (ruleId && paramId) {
          if (!paramsByRule[ruleId]) {
            paramsByRule[ruleId] = [];
          }
          if (paramsByRule[ruleId].indexOf(paramId) === -1) {
            paramsByRule[ruleId].push(paramId);
          }
        }
      });
    });
    var mapping = service.length ? service : components;
    var checks = [];
    var seen = {};
    mapping.forEach(function (comp) {
      if (isValidationComponent(comp) && service.length) {
        return;
      }
      (comp["control-implementations"] || []).forEach(function (implementation) {
        var implProps = propsMap(implementation);
        (implementation["implemented-requirements"] || []).forEach(function (req) {
          var controlId = req["control-id"];
          if (!controlId || String(controlId).toLowerCase() === "na") {
            return;
          }
          controlId = String(controlId);
          var ruleIds = collectNamed(req.props, ["Rule_Id", "rule-id", "rule_id"]);
          if (!ruleIds.length) {
            ruleIds = collectNamed(req.props, ["Check_Id", "check-id", "check_id"]);
          }
          var irProps = propsMap(req);
          var irParamIds = (req["set-parameters"] || [])
            .filter(function (item) {
              return item["param-id"];
            })
            .map(function (item) {
              return String(item["param-id"]);
            });
          var titleFallback = String(req.description || comp.title || controlId);
          ruleIds.forEach(function (ruleId) {
            var key = ruleId + "|" + controlId;
            if (seen[key]) {
              return;
            }
            seen[key] = true;
            checks.push(
              specFromGroups(
                ruleId,
                controlId,
                ruleSets[ruleId] || {},
                irProps,
                implProps,
                (paramsByRule[ruleId] || []).concat(irParamIds),
                titleFallback,
                String(req.description || "")
              )
            );
          });
        });
      });
    });
    if (!checks.length) {
      throw new Error(
        "no check mappings found on the component-definition. Add implemented-requirement Rule_Id props, or a checks.json."
      );
    }
    var meta = cdef.metadata || {};
    return {
      schema_version: "1.0",
      title: String(meta.title || "Component definition checks"),
      source: source || "oscal-component-definition",
      checks: checks,
    };
  }

  function effectiveCheckId(spec) {
    return (spec && spec.check_id) || (spec && spec.rule_id) || "";
  }

  function ingestCatalog(bundle, catalog) {
    var meta = catalog.metadata || {};
    if (meta.title) {
      bundle.titles.push(String(meta.title));
    }
    (catalog.params || []).forEach(function (param) {
      var value = paramValue(param);
      if (value !== null && param.id) {
        bundle.params[String(param.id)] = value;
      }
    });
    walkControls(catalog, function (control) {
      if (!control.id) {
        return;
      }
      var record = {
        control_id: String(control.id),
        title: String(control.title || control.id),
        statement: partText(control, "statement"),
        statement_id: statementId(control),
        params: {},
        param_labels: {},
        props: propsMap(control),
      };
      (control.params || []).forEach(function (param) {
        if (!param.id) {
          return;
        }
        var pid = String(param.id);
        if (param.label) {
          record.param_labels[pid] = String(param.label);
        }
        var value = paramValue(param);
        if (value !== null) {
          record.params[pid] = value;
          bundle.params[pid] = value;
        }
      });
      bundle.controls[record.control_id] = record;
    });
  }

  function loadBundle(documents) {
    var bundle = { controls: {}, params: {}, titles: [], kinds: [], componentDefinitions: [] };
    (documents || []).forEach(function (data) {
      if (!data || typeof data !== "object") {
        throw new Error("OSCAL document must be a JSON object");
      }
      if (data.catalog) {
        bundle.kinds.push("catalog");
        ingestCatalog(bundle, data.catalog);
      } else if (data.profile) {
        bundle.kinds.push("profile");
        var meta = data.profile.metadata || {};
        if (meta.title) {
          bundle.titles.push(String(meta.title));
        }
        var modify = data.profile.modify || {};
        (modify["set-parameters"] || []).forEach(function (item) {
          if (item["param-id"] && item.values && item.values.length) {
            bundle.params[String(item["param-id"])] = String(item.values[0]);
          }
        });
      } else if (data["component-definition"]) {
        bundle.kinds.push("component-definition");
        ingestComponentDefinition(bundle, data["component-definition"]);
      } else {
        throw new Error("Unrecognised OSCAL document: expected a catalog, profile, or component-definition.");
      }
    });
    return bundle;
  }

  function parseChecks(data) {
    if (data && data["component-definition"]) {
      return manifestFromComponentDefinition(data["component-definition"], data.source || "oscal-component-definition");
    }
    if (!data || !Array.isArray(data.checks) || !data.checks.length) {
      throw new Error("checks.json must contain a non-empty checks array");
    }
    return {
      schema_version: String(data.schema_version || "1.0"),
      title: String(data.title || "Checks"),
      source: data.source || null,
      checks: data.checks.map(function (item, index) {
        if (!item || typeof item !== "object") {
          throw new Error("checks[" + index + "] must be an object");
        }
        if (!item.rule_id || !item.control_id) {
          throw new Error("checks[" + index + "] needs rule_id and control_id");
        }
        var checkType = item.check_type || "automated";
        return {
          rule_id: String(item.rule_id),
          control_id: String(item.control_id),
          check_type: checkType,
          engine: String(item.engine || (checkType === "manual" ? "none" : "opa")),
          policy: item.policy || null,
          query: item.query || null,
          params: Array.isArray(item.params) ? item.params.map(String) : [],
          ksi_id: item.ksi_id || null,
          title: item.title || null,
          description: item.description || null,
          evidence: item.evidence || null,
          evidence_needed: item.evidence_needed || null,
          review_status: item.review_status || null,
          payload_type: item.payload_type ? String(item.payload_type) : null,
          payload_versions: Array.isArray(item.payload_versions) ? item.payload_versions.map(String) : [],
          payload_requires: Array.isArray(item.payload_requires) ? item.payload_requires.map(String) : [],
          check_id: item.check_id ? String(item.check_id) : null,
        };
      }),
    };
  }

  function libraryById(library) {
    var map = {};
    ((library && library.checks) || []).forEach(function (check) {
      map[check.rule_id] = check;
    });
    return map;
  }

  function suggestControl(check, controls) {
    var records = Object.keys(controls).map(function (id) {
      return controls[id];
    });
    var i;
    for (i = 0; i < records.length; i += 1) {
      if (records[i].props && records[i].props["rule-id"] === check.rule_id) {
        return records[i].control_id;
      }
    }
    var wanted = {};
    (check.suggested_controls || []).forEach(function (item) {
      wanted[normalizeControlId(item)] = true;
    });
    wanted[normalizeControlId(check.rule_id)] = true;
    for (i = 0; i < records.length; i += 1) {
      var cid = normalizeControlId(records[i].control_id);
      var match = Object.keys(wanted).some(function (item) {
        return cid === item || (item.length >= 4 && (cid.indexOf(item) !== -1 || item.indexOf(cid) !== -1));
      });
      if (match) {
        return records[i].control_id;
      }
    }
    var keywords = String(check.title || "")
      .toLowerCase()
      .match(/[a-z0-9]{4,}/g) || [];
    var best = null;
    records.forEach(function (record) {
      var hay = (record.title + " " + (record.statement || "")).toLowerCase();
      var score = 0;
      keywords.forEach(function (word) {
        if (hay.indexOf(word) !== -1) {
          score += 1;
        }
      });
      if (score >= 2 && (!best || score > best[0])) {
        best = [score, record.control_id];
      }
    });
    return best ? best[1] : null;
  }

  function manifestFromLibrary(library, bundle, selectedIds) {
    var libMap = libraryById(library);
    var ids = selectedIds || Object.keys(libMap);
    var checks = [];
    ids.forEach(function (ruleId) {
      var check = libMap[ruleId];
      if (!check) {
        return;
      }
      var controlId = suggestControl(check, bundle.controls) || normalizeControlId(check.rule_id);
      checks.push({
        rule_id: check.rule_id,
        control_id: controlId,
        check_type: check.check_type,
        engine: check.check_type === "manual" ? "none" : check.engine || "opa",
        policy: check.policy ? "library/" + check.rule_id + ".rego" : null,
        params: (check.params || []).map(function (param) {
          return param.id;
        }),
        ksi_id: check.ksi_id || null,
        title: check.title,
        description: check.description,
        evidence_needed: check.evidence_needed || null,
        payload_type: check.payload_type || null,
        payload_versions: check.payload_versions || [],
        payload_requires: check.payload_requires || [],
      });
    });
    if (!checks.length) {
      throw new Error("No library checks selected.");
    }
    return { schema_version: "1.0", title: "Library checks", source: "library", checks: checks };
  }

  function findControl(bundle, controlId) {
    if (bundle.controls[controlId]) {
      return bundle.controls[controlId];
    }
    var wanted = normalizeControlId(controlId);
    var ids = Object.keys(bundle.controls);
    for (var i = 0; i < ids.length; i += 1) {
      if (normalizeControlId(ids[i]) === wanted) {
        return bundle.controls[ids[i]];
      }
    }
    return null;
  }

  function resolveParams(spec, bundle) {
    var control = findControl(bundle, spec.control_id);
    var merged = {};
    if (control) {
      Object.keys(control.params).forEach(function (key) {
        merged[key] = control.params[key];
      });
    }
    Object.keys(bundle.params).forEach(function (key) {
      merged[key] = bundle.params[key];
    });
    var params = {};
    var wanted = spec.params || [];
    wanted.forEach(function (pid) {
      if (pid in merged) {
        params[pid] = merged[pid];
      }
    });
    if (control) {
      var extras = [];
      Object.keys(control.params).forEach(function (key) {
        if (wanted.indexOf(key) === -1) {
          extras.push(control.params[key]);
        }
      });
      var extraIndex = 0;
      wanted.forEach(function (pid) {
        if (!(pid in params) && extraIndex < extras.length) {
          params[pid] = extras[extraIndex];
          extraIndex += 1;
        }
      });
      Object.keys(control.params).forEach(function (key) {
        if (!(key in params)) {
          params[key] = merged[key] !== undefined ? merged[key] : control.params[key];
        }
      });
    }
    return params;
  }

  function aliasLibraryParams(spec, params, libraryCheck) {
    var out = {};
    Object.keys(params).forEach(function (key) {
      out[key] = params[key];
    });
    if (!libraryCheck || !libraryCheck.params) {
      return out;
    }
    var specParams = spec.params || [];
    libraryCheck.params.forEach(function (param, index) {
      if (out[param.id]) {
        return;
      }
      if (specParams[index] && out[specParams[index]]) {
        out[param.id] = out[specParams[index]];
        return;
      }
      var extras = Object.keys(params).filter(function (key) {
        return specParams.indexOf(key) === -1;
      });
      if (extras[index]) {
        out[param.id] = params[extras[index]];
      } else if (param.values && param.values[0]) {
        out[param.id] = param.values[0];
      }
    });
    return out;
  }

  function parseEvidence(data) {
    if (!data || typeof data !== "object") {
      throw evidenceError("document must be a JSON object");
    }
    if (data.enact_evidence) {
      return { kind: "envelope", data: data, envelopes: [data] };
    }
    if (data.enact_evidence_bundle) {
      var items = data.items;
      if (!Array.isArray(items)) {
        throw evidenceError("bundle items must be an array");
      }
      return { kind: "bundle", data: data, envelopes: items };
    }
    return { kind: "legacy", data: data, envelopes: [] };
  }

  function legacyPayload(data) {
    if (data.iam && typeof data.iam === "object") {
      return data.iam;
    }
    if (data.payload && typeof data.payload === "object") {
      return data.payload;
    }
    return {};
  }

  function collectorLabel(collector) {
    var name = String((collector && collector.name) || "unknown");
    var version = String((collector && collector.version) || "");
    var kind = String((collector && collector.kind) || "unknown");
    if (version) {
      return name + "@" + version + " (" + kind + ")";
    }
    return name + " (" + kind + ")";
  }

  function requireFields(spec, payload) {
    var missing = (spec.payload_requires || []).filter(function (field) {
      return !(field in payload);
    });
    if (missing.length) {
      throw evidenceError(
        "check " +
          spec.rule_id +
          " requires payload field(s) " +
          missing.join(", ") +
          " (payload_type " +
          spec.payload_type +
          ")"
      );
    }
  }

  function bindCheck(spec, parsed) {
    if (parsed.kind === "envelope" || parsed.kind === "bundle") {
      if (!spec.payload_type) {
        return Promise.resolve({ mode: "legacy", payload: {}, provenance: {} });
      }
      var matches = parsed.envelopes.filter(function (item) {
        return item.payload_type === spec.payload_type;
      });
      if (!matches.length) {
        return Promise.reject(
          evidenceError("no envelope with payload_type " + spec.payload_type + " for check " + spec.rule_id)
        );
      }
      var envelope = matches[0];
      var version = String(envelope.payload_version || "");
      var allowed = spec.payload_versions || [];
      if (allowed.length && allowed.indexOf(version) === -1) {
        return Promise.reject(
          evidenceError(
            "payload version " + version + " is not accepted by check " + spec.rule_id + " (allowed: " + allowed.join(", ") + ")"
          )
        );
      }
      var payload = envelope.payload;
      if (!payload || typeof payload !== "object") {
        return Promise.reject(evidenceError("envelope payload for " + spec.payload_type + " must be an object"));
      }
      try {
        requireFields(spec, payload);
      } catch (err) {
        return Promise.reject(err);
      }
      return sha256Hex(canonicalJson(payload)).then(function (digest) {
        var collector = envelope.collector && typeof envelope.collector === "object" ? envelope.collector : {};
        return {
          mode: "envelope",
          payload: payload,
          provenance: {
            "evidence-id": String(envelope.id || ""),
            "payload-type": String(envelope.payload_type || ""),
            "payload-version": String(envelope.payload_version || ""),
            "collected-at": String(envelope.collected_at || ""),
            collector: collectorLabel(collector),
            "evidence-sha256": digest,
          },
        };
      });
    }
    var payloadLegacy = legacyPayload(parsed.data);
    if (!spec.payload_type) {
      return Promise.resolve({ mode: "legacy", payload: payloadLegacy, provenance: {} });
    }
    try {
      requireFields(spec, payloadLegacy);
    } catch (err) {
      return Promise.reject(err);
    }
    var version = (spec.payload_versions && spec.payload_versions[0]) || "1.0";
    return sha256Hex(canonicalJson(payloadLegacy)).then(function (digest) {
      return {
        mode: "legacy",
        payload: payloadLegacy,
        provenance: {
          "evidence-id": "legacy-" + digest.slice(0, 12),
          "payload-type": spec.payload_type,
          "payload-version": version,
          collector: "enact/" + VERSION + " (legacy)",
          "evidence-sha256": digest,
        },
      };
    });
  }

  function buildOpaInput(spec, inputData, params, bound) {
    var checkMeta = {
      rule_id: spec.rule_id,
      control_id: spec.control_id,
      ksi_id: spec.ksi_id,
    };
    if (bound.mode === "envelope") {
      return { payload: bound.payload, oscal_params: params, check: checkMeta };
    }
    var payload = {
      config: inputData.config !== undefined ? inputData.config : inputData,
      oscal_params: params,
      check: checkMeta,
    };
    if (inputData.iam && payload.iam === undefined) {
      payload.iam = inputData.iam;
    }
    Object.keys(inputData).forEach(function (key) {
      if (!(key in payload)) {
        payload[key] = inputData[key];
      }
    });
    if (!("payload" in payload)) {
      payload.payload = bound.payload;
    }
    return payload;
  }

  function entrypointFor(spec, libraryCheck) {
    if (libraryCheck && libraryCheck.entrypoint) {
      return libraryCheck.entrypoint;
    }
    if (spec.query && spec.query.indexOf("data.") === 0) {
      return spec.query.slice(5).replace(/\./g, "/");
    }
    return null;
  }

  function interpretWasm(policy, input, entrypoint) {
    if (!policy || typeof policy.evaluate !== "function") {
      throw new Error("WASM policy is not loaded.");
    }
    if (!entrypoint) {
      throw new Error("Custom checks? Use the Enact CLI");
    }
    var loader = root.EnactOpa || (typeof require === "function" ? require("./opa-eval.js") : null);
    if (!loader) {
      throw new Error("OPA wasm loader is missing.");
    }
    var raw = policy.evaluate(input, entrypoint);
    return loader.interpretResult(raw);
  }

  function displayTitle(spec) {
    return spec.title || spec.rule_id;
  }

  function runOne(spec, ctx) {
    var params = resolveParams(spec, ctx.bundle);
    var libraryCheck = ctx.libMap[spec.rule_id];
    var opaParams = aliasLibraryParams(spec, params, libraryCheck);

    function finish(outcome) {
      outcome.spec = spec;
      outcome.params_used = params;
      return outcome;
    }

    if (spec.check_type === "manual") {
      var needed = spec.evidence_needed || "This control is not automated. Attach reviewer evidence.";
      var evidence = [];
      if (spec.evidence) {
        evidence.push({ description: needed, href: spec.evidence });
      }
      return Promise.resolve(
        finish({
          status: "not_automated",
          message: needed,
          engine: "none",
          evidence: evidence,
          raw: {},
          evidence_provenance: null,
        })
      );
    }

    var inputData = ctx.evidence || {};
    var parsed;
    try {
      parsed = parseEvidence(inputData);
    } catch (err) {
      return Promise.resolve(
        finish({
          status: "error",
          message: err.message,
          engine: spec.engine,
          evidence: [],
          raw: {},
          evidence_provenance: null,
        })
      );
    }
    var usedLegacy = parsed.kind === "legacy" && Object.keys(inputData).length > 0;
    return bindCheck(spec, parsed)
      .then(function (bound) {
        var opaInput = buildOpaInput(spec, inputData, opaParams, bound);
        var evaluated;
        try {
          evaluated = interpretWasm(ctx.policy, opaInput, entrypointFor(spec, libraryCheck));
        } catch (err) {
          return finish({
            status: "error",
            message: err.message || String(err),
            engine: spec.engine,
            evidence: [],
            raw: {},
            evidence_provenance: bound.provenance || null,
            used_legacy: usedLegacy,
          });
        }
        var evidenceItems = [
          {
            description: "Rego policy " + (spec.policy || spec.rule_id) + " evaluated against local input.",
            href: spec.policy || null,
          },
        ];
        var outcome = {
          status: evaluated.passed ? "pass" : "fail",
          message: evaluated.message,
          engine: "opa",
          evidence: evidenceItems,
          raw: { input: opaInput, result: evaluated.raw || evaluated },
          evidence_provenance: bound.provenance || null,
          used_legacy: usedLegacy,
        };
        if (spec.review_status === "draft") {
          outcome.status = "draft";
          outcome.message = "Draft (unreviewed): " + evaluated.message;
        } else if (spec.check_type === "hybrid" && outcome.status === "pass") {
          var hybridNeeded =
            spec.evidence_needed || "Automated portion passed; a person still needs to attach evidence.";
          if (spec.evidence) {
            evidenceItems.push({ description: hybridNeeded, href: spec.evidence });
          }
          outcome.status = "needs_evidence";
          outcome.message = hybridNeeded;
        }
        return finish(outcome);
      })
      .catch(function (err) {
        return finish({
          status: "error",
          message: err.message || String(err),
          engine: spec.engine,
          evidence: [],
          raw: {},
          evidence_provenance: null,
          used_legacy: usedLegacy,
        });
      });
  }

  function countsOf(outcomes) {
    var tallies = {
      pass: 0,
      fail: 0,
      not_automated: 0,
      needs_evidence: 0,
      error: 0,
      draft: 0,
    };
    outcomes.forEach(function (outcome) {
      tallies[outcome.status] += 1;
    });
    return tallies;
  }

  function prop(name, value, namespaced) {
    if (!value) {
      return null;
    }
    var item = { name: name, value: String(value) };
    if (namespaced !== false) {
      item.ns = NS;
    }
    return item;
  }

  function props() {
    var items = [];
    for (var i = 0; i < arguments.length; i += 1) {
      if (arguments[i]) {
        items.push(arguments[i]);
      }
    }
    return items;
  }

  function statementTarget(outcome, bundle) {
    var control = findControl(bundle, outcome.spec.control_id);
    if (control && control.statement_id) {
      return control.statement_id;
    }
    return outcome.spec.control_id + "_smt";
  }

  function observationMethods(outcome) {
    if (outcome.spec.check_type === "manual") {
      return ["EXAMINE"];
    }
    return ["TEST"];
  }

  function writeObservation(run, outcome) {
    return makeUuid("obs", outcome.spec.rule_id, outcome.spec.control_id, outcome.status, outcome.message).then(
      function (obsUuid) {
        var paramProps = [];
        Object.keys(outcome.params_used || {}).forEach(function (key) {
          paramProps.push(prop("param-" + key, outcome.params_used[key]));
        });
        var provenanceProps = [];
        Object.keys(outcome.evidence_provenance || {}).forEach(function (name) {
          provenanceProps.push(prop(name, outcome.evidence_provenance[name]));
        });
        return makeUuid("subj", outcome.spec.rule_id, outcome.spec.control_id, outcome.status).then(function (subjUuid) {
          var observation = {
            uuid: obsUuid,
            title: displayTitle(outcome.spec),
            description: outcome.message,
            props: props(
              prop("assessment-rule-id", outcome.spec.rule_id, false),
              prop("Check_Id", effectiveCheckId(outcome.spec), false),
              prop("rule-id", outcome.spec.rule_id),
              prop("control-id", outcome.spec.control_id, false),
              prop("check-type", outcome.spec.check_type),
              prop("result", outcome.status),
              prop("status", outcome.status === "draft" ? outcome.status : null),
              prop("review-status", outcome.spec.review_status),
              prop("engine", outcome.engine),
              prop("ksi-id", outcome.spec.ksi_id)
            )
              .concat(paramProps.filter(Boolean))
              .concat(provenanceProps.filter(Boolean)),
            methods: observationMethods(outcome),
            types: outcome.status === "pass" || outcome.status === "fail" ? ["finding"] : ["control-objective"],
            collected: nowIso(run.endedIso),
            subjects: [
              {
                "subject-uuid": subjUuid,
                type: "inventory-item",
                title: "Enact check: " + outcome.spec.rule_id,
                props: [
                  { name: "resource-id", value: effectiveCheckId(outcome.spec) },
                  { name: "result", value: outcome.status },
                  { name: "evaluated-on", value: nowIso(run.endedIso) },
                  { name: "reason", value: String(outcome.message || "").replace(/\n/g, " ") },
                ],
              },
            ],
          };
          if (outcome.evidence && outcome.evidence.length) {
            observation["relevant-evidence"] = outcome.evidence.map(function (item) {
              var row = { description: item.description };
              if (item.href) {
                row.href = item.href;
              }
              return row;
            });
          }
          return observation;
        });
      }
    );
  }

  function writeFinding(run, outcome, observationUuid, bundle) {
    if (outcome.status === "not_automated" || outcome.status === "needs_evidence" || outcome.status === "draft") {
      return Promise.resolve(null);
    }
    var state;
    var reason;
    if (outcome.status === "error") {
      state = "not-satisfied";
      reason = "other";
    } else if (outcome.status === "fail") {
      state = "not-satisfied";
      reason = "fail";
    } else if (outcome.status === "pass") {
      state = "satisfied";
      reason = "pass";
    } else {
      return Promise.resolve(null);
    }
    return makeUuid("finding", outcome.spec.rule_id, outcome.spec.control_id, outcome.status).then(function (id) {
      return {
        uuid: id,
        title: outcome.spec.control_id + ": " + displayTitle(outcome.spec),
        description: outcome.message,
        props: props(
          prop("rule-id", outcome.spec.rule_id),
          prop("control-id", outcome.spec.control_id, false),
          prop("ksi-id", outcome.spec.ksi_id)
        ),
        target: {
          type: "statement-id",
          "target-id": statementTarget(outcome, bundle),
          status: { state: state, reason: reason },
        },
        "related-observations": [{ "observation-uuid": observationUuid }],
      };
    });
  }

  function metadata(run, title) {
    return {
      title: title,
      "last-modified": nowIso(run.endedIso),
      version: VERSION,
      "oscal-version": OSCAL_VERSION,
      props: props(
        prop("generator", "Enact " + VERSION),
        prop("source-manifest", run.manifest.source),
        prop("input-label", run.inputLabel)
      ),
    };
  }

  function writeOscal(run, bundle) {
    var includeControls = [];
    var seen = {};
    run.outcomes.forEach(function (outcome) {
      if (!seen[outcome.spec.control_id]) {
        includeControls.push({ "control-id": outcome.spec.control_id });
        seen[outcome.spec.control_id] = true;
      }
    });
    return Promise.all(
      run.outcomes.map(function (outcome) {
        return writeObservation(run, outcome).then(function (observation) {
          return writeFinding(run, outcome, observation.uuid, bundle).then(function (finding) {
            return { observation: observation, finding: finding };
          });
        });
      })
    ).then(function (rows) {
      var observations = rows.map(function (row) {
        return row.observation;
      });
      var findings = rows
        .map(function (row) {
          return row.finding;
        })
        .filter(Boolean);
      return Promise.all([
        makeUuid("result", run.title, run.startedIso),
        makeUuid("ar", run.title, run.startedIso),
      ]).then(function (ids) {
        var result = {
          uuid: ids[0],
          title: run.title,
          description:
            "Automated and manual control checks run by Enact. Every observation and finding is traced to a control ID.",
          start: nowIso(run.startedIso),
          end: nowIso(run.endedIso),
          "reviewed-controls": { "control-selections": [{ "include-controls": includeControls }] },
          observations: observations,
        };
        if (findings.length) {
          result.findings = findings;
        }
        return {
          "assessment-results": {
            uuid: ids[1],
            metadata: metadata(run, "OSCAL assessment results from Enact"),
            "import-ap": {
              href: "assessment-plan.json",
              remarks:
                "Enact synthesises assessment results in CI without a separate assessment-plan document. Replace this href when you have one.",
            },
            results: [result],
          },
        };
      });
    });
  }

  function writePoam(run, bundle) {
    var failures = run.outcomes.filter(function (outcome) {
      return outcome.status === "fail" || outcome.status === "error";
    });
    return Promise.all(
      failures.map(function (outcome) {
        return writeObservation(run, outcome).then(function (observation) {
          return writeFinding(run, outcome, observation.uuid, bundle).then(function (finding) {
            if (!finding) {
              return null;
            }
            return makeUuid("poam", outcome.spec.rule_id, outcome.spec.control_id, outcome.status).then(function (id) {
              return {
                item: {
                  uuid: id,
                  title: "Remediate " + outcome.spec.control_id + " (" + outcome.spec.rule_id + ")",
                  description:
                    "Automated check " +
                    outcome.spec.rule_id +
                    " failed for control " +
                    outcome.spec.control_id +
                    ". " +
                    outcome.message,
                  props: props(
                    prop("rule-id", outcome.spec.rule_id),
                    prop("control-id", outcome.spec.control_id, false),
                    prop("ksi-id", outcome.spec.ksi_id)
                  ),
                  "related-findings": [{ "finding-uuid": finding.uuid }],
                  "related-observations": [{ "observation-uuid": observation.uuid }],
                },
                observation: observation,
                finding: finding,
              };
            });
          });
        });
      })
    ).then(function (rows) {
      var kept = rows.filter(Boolean);
      var items = kept.map(function (row) {
        return row.item;
      });
      return Promise.all([
        makeUuid("poam-doc", run.title, run.startedIso),
        items.length ? Promise.resolve(null) : makeUuid("poam-none", run.title),
      ]).then(function (ids) {
        var document = {
          "plan-of-action-and-milestones": {
            uuid: ids[0],
            metadata: metadata(run, "POA&M items from Enact failures"),
            "import-ssp": {
              href: "system-security-plan.json",
              remarks: "Optional SSP/SDR href. Enact emits POA&M items from check failures only.",
            },
            "poam-items": items.length
              ? items
              : [
                  {
                    uuid: ids[1],
                    title: "No open items",
                    description: "All automated checks passed. Manual and hybrid controls still need evidence.",
                  },
                ],
          },
        };
        var root = document["plan-of-action-and-milestones"];
        if (kept.length) {
          root.observations = kept.map(function (row) {
            return row.observation;
          });
          root.findings = kept.map(function (row) {
            return row.finding;
          });
        }
        return document;
      });
    });
  }

  function poamRef(outcome) {
    return makeUuid("poam", outcome.spec.rule_id, outcome.spec.control_id, outcome.status).then(function (id) {
      return { uuid: id, title: "Remediate " + outcome.spec.control_id + " (" + outcome.spec.rule_id + ")" };
    });
  }

  function renderHtml(run, assets) {
    assets = assets || {};
    var counts = countsOf(run.outcomes);
    var passed = counts.pass;
    var failed = counts.fail + counts.error;
    var manual = counts.not_automated + counts.needs_evidence;
    var draft = counts.draft;
    var automated = passed + failed;
    var rate = automated ? Math.round((100 * passed) / automated) : 0;
    var rateHint = automated ? passed + " of " + automated + " automated checks" : "No automated checks in this run";
    var generated = escapeHtml(nowIso(run.endedIso));
    var rowsHtml = "";
    var pending = Promise.resolve();
    run.outcomes.forEach(function (outcome, index) {
      pending = pending.then(function () {
        var expandable = outcome.status === "fail" || outcome.status === "error";
        var findingId = "finding-" + index;
        var expand = "";
        if (expandable) {
          expand =
            '<button type="button" class="expand" data-expand aria-expanded="false" aria-controls="' +
            findingId +
            '" aria-label="Show finding for ' +
            escapeHtml(outcome.spec.control_id) +
            '">▸</button>';
        }
        var search = [
          outcome.spec.control_id,
          outcome.spec.rule_id,
          outcome.spec.check_type,
          outcome.status,
          HTML_STATUS[outcome.status],
          outcome.message,
          outcome.spec.ksi_id || "",
          displayTitle(outcome.spec),
        ]
          .join(" ")
          .toLowerCase();
        rowsHtml +=
          '<tr class="check" data-status="' +
          escapeHtml(outcome.status) +
          '" data-search="' +
          escapeHtml(search) +
          '">' +
          '<td class="ctrl">' +
          expand +
          "<code>" +
          escapeHtml(outcome.spec.control_id) +
          "</code></td>" +
          "<td><code>" +
          escapeHtml(outcome.spec.rule_id) +
          "</code></td>" +
          '<td><span class="type">' +
          escapeHtml(outcome.spec.check_type) +
          "</span></td>" +
          '<td><span class="pill ' +
          escapeHtml(outcome.status) +
          '">' +
          escapeHtml(HTML_STATUS[outcome.status]) +
          "</span></td></tr>";
        if (!expandable) {
          return;
        }
        return poamRef(outcome).then(function (ref) {
          var params =
            Object.keys(outcome.params_used || {})
              .map(function (key) {
                return escapeHtml(key) + "=" + escapeHtml(outcome.params_used[key]);
              })
              .join(", ") || "None recorded.";
          var evidenceBits = (outcome.evidence || [])
            .map(function (item) {
              var bit = escapeHtml(item.description);
              if (item.href) {
                bit += " <code>" + escapeHtml(item.href) + "</code>";
              }
              return "<p>" + bit + "</p>";
            })
            .join("");
          rowsHtml +=
            '<tr class="finding" id="' +
            findingId +
            '" hidden><td colspan="4"><div class="finding-list">' +
            '<div class="finding-item"><span class="dot fail" aria-hidden="true"></span><div><h3>Finding</h3><p>' +
            escapeHtml(outcome.message) +
            "</p></div></div>" +
            '<div class="finding-item"><span class="dot" aria-hidden="true"></span><div><h3>Parameters</h3><p>' +
            params +
            "</p></div></div>" +
            '<div class="finding-item"><span class="dot" aria-hidden="true"></span><div><h3>POA&amp;M</h3><p>' +
            escapeHtml(ref.title) +
            " — <code>" +
            escapeHtml(ref.uuid) +
            "</code></p></div></div>" +
            '<div class="finding-item"><span class="dot" aria-hidden="true"></span><div><h3>Evidence</h3>' +
            (evidenceBits || "<p>No file attached.</p>") +
            "</div></div></div></td></tr>";
        });
      });
    });
    return pending.then(function () {
      var themeCss = assets.themeCss || "";
      var themeJs = assets.themeJs || "";
      return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" +
        '  <meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'none\'; font-src \'none\'; base-uri \'none\'; form-action \'none\'">\n' +
        "  <title>" +
        escapeHtml(run.title) +
        "</title>\n  <script>" +
        THEME_BOOTSTRAP +
        "</script>\n  <style>" +
        themeCss +
        REPORT_CSS +
        "</style>\n</head>\n<body>\n  <div class=\"wrap\">\n    <div class=\"report-head\">\n      <div>\n        <p class=\"kicker\">Enact assessment</p>\n        <h1>" +
        escapeHtml(run.title) +
        "</h1>\n      </div>\n      <div class=\"theme-toggle\"><p class=\"theme-toggle__label\" id=\"theme-toggle-label\">Appearance</p><div class=\"theme-toggle__group\" role=\"radiogroup\" aria-labelledby=\"theme-toggle-label\"><button type=\"button\" role=\"radio\" aria-checked=\"false\" data-theme-choice=\"light\">Light</button><button type=\"button\" role=\"radio\" aria-checked=\"false\" data-theme-choice=\"dark\">Dark</button><button type=\"button\" role=\"radio\" aria-checked=\"true\" data-theme-choice=\"system\">System</button></div></div>\n    </div>\n    <p class=\"lede\">Each row is a check. Pass and fail come from automation. Manual and not-checked controls still need a person — that is not a failure. Draft stubs are unreviewed and never count as passed.</p>\n    <div class=\"cards\" aria-label=\"Result counts\">\n      <article class=\"card\"><div class=\"card-top\"><span class=\"label\">Passed</span><span class=\"pill pass\">Passed</span></div><p class=\"count\">" +
        passed +
        '</p><div class="bar" role="progressbar" aria-label="Pass rate" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' +
        rate +
        '"><span style="width:' +
        rate +
        '%"></span></div><p class="hint">' +
        rate +
        "% pass rate · " +
        escapeHtml(rateHint) +
        '</p></article>\n      <article class="card"><div class="card-top"><span class="label">Failed</span><span class="pill fail">Failed</span></div><p class="count">' +
        failed +
        "</p><p class=\"hint\">Automated and hybrid failures become POA&amp;M items.</p></article>\n      <article class=\"card\"><div class=\"card-top\"><span class=\"label\">Manual / Not checked</span><span class=\"pill wait\">Manual</span></div><p class=\"count\">" +
        manual +
        "</p><p class=\"hint\">Recorded as observations, not as failures.</p></article>\n      <article class=\"card\"><div class=\"card-top\"><span class=\"label\">Draft</span><span class=\"pill draft\">Draft</span></div><p class=\"count\">" +
        draft +
        "</p><p class=\"hint\">Generated stubs. Untrusted until <code>enact checks review</code>.</p></article>\n    </div>\n    <div class=\"toolbar\"><label class=\"visually-hidden\" for=\"q\" style=\"position:absolute;left:-9999px\">Search controls</label><input id=\"q\" type=\"search\" placeholder=\"Search control ID, rule ID, or message\"><div class=\"filters\" role=\"group\" aria-label=\"Filter by status\"><button type=\"button\" data-filter=\"all\" aria-pressed=\"true\">All</button><button type=\"button\" data-filter=\"pass\">Passed</button><button type=\"button\" data-filter=\"fail\">Failed</button><button type=\"button\" data-filter=\"manual\">Manual</button><button type=\"button\" data-filter=\"draft\">Draft</button></div></div>\n    <div class=\"table-wrap\"><table><thead><tr><th>Control ID</th><th>Rule ID</th><th>Check type</th><th>Status</th></tr></thead><tbody>" +
        rowsHtml +
        '</tbody></table><p class="empty" id="empty" hidden>No checks match this search or filter.</p></div>\n    <footer class="note">Generated by Enact ' +
        escapeHtml(VERSION) +
        " at " +
        generated +
        ". Ran locally; nothing was sent off this machine.</footer>\n  </div>\n  <script>" +
        themeJs +
        REPORT_JS +
        "</script>\n</body>\n</html>\n"
      );
    });
  }

  function runAssessment(options) {
    options = options || {};
    var documents = options.catalogs || (options.catalog ? [options.catalog] : []);
    if (options.checks && options.checks["component-definition"]) {
      documents = documents.concat([options.checks]);
    }
    if (!documents.length) {
      return Promise.reject(new Error("Open a catalog JSON, or use the bundled example."));
    }
    var bundle = loadBundle(documents);
    var library = options.library || {};
    var manifest = options.checks
      ? parseChecks(options.checks)
      : manifestFromLibrary(library, bundle, options.selectedIds);
    var startedIso = options.startedIso || new Date().toISOString();
    var endedIso = options.endedIso || startedIso;
    var title = options.title || bundle.titles[0] || manifest.title || "Enact assessment";
    var ctx = {
      bundle: bundle,
      policy: options.policy,
      libMap: libraryById(library),
      evidence: options.evidence || {},
    };
    var usedLegacy = false;
    return manifest.checks
      .reduce(function (chain, spec) {
        return chain.then(function (outcomes) {
          return runOne(spec, ctx).then(function (outcome) {
            if (outcome.used_legacy) {
              usedLegacy = true;
            }
            outcomes.push(outcome);
            return outcomes;
          });
        });
      }, Promise.resolve([]))
      .then(function (outcomes) {
        var run = {
          title: title,
          startedIso: startedIso,
          endedIso: endedIso,
          manifest: manifest,
          outcomes: outcomes,
          catalog_title: bundle.titles[0] || null,
          inputLabel: options.inputLabel || null,
          legacy_evidence: usedLegacy,
        };
        return Promise.all([writeOscal(run, bundle), writePoam(run, bundle), renderHtml(run, options.reportAssets)]).then(
          function (written) {
            return {
              run: run,
              bundle: bundle,
              oscal: written[0],
              poam: written[1],
              html: written[2],
              counts: countsOf(outcomes),
              outcomes: outcomes.map(function (outcome) {
                return {
                  rule_id: outcome.spec.rule_id,
                  control_id: outcome.spec.control_id,
                  status: outcome.status,
                  message: outcome.message,
                  check_type: outcome.spec.check_type,
                  params_used: outcome.params_used,
                };
              }),
            };
          }
        );
      });
  }

  function libraryEntrypoint(policyText) {
    var match = PACKAGE_RE.exec(policyText || "");
    if (!match) {
      return null;
    }
    return match[1].replace(/\./g, "/") + "/result";
  }

  var api = {
    VERSION: VERSION,
    NS: NS,
    loadBundle: loadBundle,
    parseChecks: parseChecks,
    manifestFromComponentDefinition: manifestFromComponentDefinition,
    groupPropsByRemarks: groupPropsByRemarks,
    suggestControl: suggestControl,
    manifestFromLibrary: manifestFromLibrary,
    resolveParams: resolveParams,
    runAssessment: runAssessment,
    writeOscal: writeOscal,
    writePoam: writePoam,
    renderHtml: renderHtml,
    countsOf: countsOf,
    libraryById: libraryById,
    libraryEntrypoint: libraryEntrypoint,
    normalizeControlId: normalizeControlId,
    THEME_BOOTSTRAP: THEME_BOOTSTRAP,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.Enact = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
