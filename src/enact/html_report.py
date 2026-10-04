"""Self-contained HTML assessment report. No network fetches; works offline."""

from __future__ import annotations

import html

from enact import __version__
from enact.models import AssessmentRun, CheckOutcome, OutcomeStatus
from enact.oscal_io import OscalBundle
from enact.theme import (
    report_csp,
    theme_bootstrap_script_tag,
    theme_js,
    theme_stylesheet,
    theme_toggle_html,
)

HTML_STATUS: dict[OutcomeStatus, str] = {
    "pass": "Passed",
    "fail": "Failed",
    "not_automated": "Manual",
    "needs_evidence": "Not checked",
    "error": "Failed",
}

REPORT_CSS = """
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  min-height: 100vh;
  font: 15px/1.5 var(--font);
  background: var(--bg);
  color: var(--ink);
}
a { color: var(--accent); }
a:hover { color: var(--accent-hover); }
:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
.wrap { max-width: var(--max); margin: 0 auto; padding: 1.5rem 1.25rem 2.5rem; }
.kicker {
  margin: 0 0 .35rem;
  font-size: .75rem;
  font-weight: 650;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
}
h1 { margin: 0 0 .45rem; font-size: 1.7rem; letter-spacing: -.02em; }
.lede { margin: 0 0 1.25rem; color: var(--muted); max-width: 46rem; }
.report-head {
  display: flex; flex-wrap: wrap; justify-content: space-between;
  gap: .8rem; align-items: flex-start; margin-bottom: .35rem;
}
.report-head h1 { margin: 0 0 .45rem; }
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .85rem;
  margin: 0 0 1.35rem;
}
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.1rem 1.05rem;
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .6rem;
  margin-bottom: .35rem;
}
.card-top .label { color: var(--muted); font-size: .92rem; }
.count { margin: 0; font-size: 2rem; font-weight: 700; letter-spacing: -.03em; }
.hint { margin: .45rem 0 0; color: var(--muted); font-size: .85rem; }
.pill {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .15rem .55rem; border-radius: 999px;
  font-size: .75rem; font-weight: 650;
}
.pill.pass { background: var(--pass-bg); color: var(--pass); }
.pill.fail, .pill.error { background: var(--fail-bg); color: var(--fail); }
.pill.not_automated, .pill.needs_evidence, .pill.wait { background: var(--wait-bg); color: var(--wait); }
.bar {
  margin-top: .7rem; height: 8px; border-radius: 999px;
  background: var(--track); overflow: hidden;
}
.bar > span { display: block; height: 100%; background: var(--accent); border-radius: inherit; }
.toolbar {
  display: flex; flex-wrap: wrap; gap: .65rem;
  align-items: center; justify-content: space-between;
  margin: 0 0 .75rem;
}
#q {
  flex: 1 1 16rem; min-width: 12rem;
  border: 1px solid var(--line); border-radius: 10px;
  padding: .55rem .75rem; font: inherit; background: var(--card); color: var(--ink);
}
.filters { display: flex; flex-wrap: wrap; gap: .35rem; }
.filters button {
  appearance: none; font: 650 13px var(--font); color: var(--muted);
  background: var(--card); border: 1px solid var(--line);
  border-radius: 999px; padding: .35rem .75rem; cursor: pointer;
}
.filters button[aria-pressed="true"] {
  background: var(--accent-soft); border-color: var(--accent); color: var(--accent);
}
.table-wrap {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); overflow: auto;
}
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: .75rem .85rem; border-bottom: 1px solid var(--line); }
th {
  font-size: .72rem; letter-spacing: .06em; text-transform: uppercase;
  color: var(--muted); font-weight: 650; background: var(--table-head);
}
tr.check:nth-child(odd of .check) td { background: var(--card); }
tr.check:nth-child(even of .check) td { background: var(--zebra); }
tr.check:last-child td, tr.finding:last-child td { border-bottom: 0; }
tr.check[hidden], tr.finding[hidden] { display: none; }
code { font-family: var(--mono); font-size: .86em; }
.type {
  color: var(--muted); font-size: .85rem; text-transform: capitalize;
}
.expand {
  appearance: none; width: 1.5rem; height: 1.5rem; margin-right: .4rem;
  border: 1px solid var(--line); border-radius: 6px; background: var(--ghost);
  color: var(--ink); cursor: pointer; vertical-align: middle; font-size: .75rem;
}
.expand[aria-expanded="true"] { background: var(--accent-soft); border-color: var(--accent); }
.ctrl { white-space: nowrap; }
.finding td { background: var(--table-head); padding: .4rem .85rem 1rem; }
.finding-list { display: grid; gap: .55rem; }
.finding-item {
  display: flex; gap: .7rem; align-items: flex-start;
  background: var(--card); border: 1px solid var(--line);
  border-radius: 10px; padding: .7rem .8rem;
}
.dot {
  width: .7rem; height: .7rem; border-radius: 999px; margin-top: .35rem;
  background: var(--line); flex: none;
}
.dot.fail { background: var(--fail); }
.finding-item h3 { margin: 0 0 .15rem; font-size: .92rem; }
.finding-item p { margin: 0; color: var(--muted); }
.empty { padding: 1.1rem .85rem; color: var(--muted); }
footer.note { margin-top: 1.2rem; color: var(--muted); font-size: .88rem; }
@media (max-width: 800px) {
  .cards { grid-template-columns: 1fr; }
  .toolbar { align-items: stretch; }
}
"""

REPORT_JS = """
(function () {
  const search = document.getElementById("q");
  const chips = document.querySelectorAll("[data-filter]");
  const rows = document.querySelectorAll("tr.check");
  const empty = document.getElementById("empty");
  let filter = "all";

  function matchesFilter(status) {
    if (filter === "all") return true;
    if (filter === "pass") return status === "pass";
    if (filter === "fail") return status === "fail" || status === "error";
    if (filter === "manual") return status === "not_automated" || status === "needs_evidence";
    return status === filter;
  }

  function apply() {
    const q = (search.value || "").trim().toLowerCase();
    let visible = 0;
    rows.forEach(function (row) {
      const status = row.getAttribute("data-status") || "";
      const hay = row.getAttribute("data-search") || "";
      const show = matchesFilter(status) && (!q || hay.indexOf(q) !== -1);
      row.hidden = !show;
      const detail = row.nextElementSibling;
      if (detail && detail.classList.contains("finding")) {
        if (!show) detail.hidden = true;
        if (!show) {
          const btn = row.querySelector("[data-expand]");
          if (btn) btn.setAttribute("aria-expanded", "false");
        }
      }
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      filter = chip.getAttribute("data-filter") || "all";
      chips.forEach(function (c) {
        c.setAttribute("aria-pressed", String(c === chip));
      });
      apply();
    });
  });
  if (search) search.addEventListener("input", apply);

  document.querySelectorAll("[data-expand]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const row = btn.closest("tr");
      if (!row) return;
      const detail = row.nextElementSibling;
      if (!detail || !detail.classList.contains("finding")) return;
      const open = detail.hidden;
      detail.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
    });
  });
})();
"""


def _poam_ref(outcome: CheckOutcome) -> tuple[str, str]:
    from enact.writers import _uuid

    item_uuid = _uuid("poam", outcome.rule_id, outcome.control_id, outcome.status)
    title = f"Remediate {outcome.control_id} ({outcome.rule_id})"
    return item_uuid, title


def _search_blob(outcome: CheckOutcome) -> str:
    parts = [
        outcome.control_id,
        outcome.rule_id,
        outcome.spec.check_type,
        outcome.status,
        HTML_STATUS[outcome.status],
        outcome.message,
        outcome.ksi_id or "",
        outcome.spec.display_title(),
    ]
    parts.extend(f"{key}={value}" for key, value in outcome.params_used.items())
    return html.escape(" ".join(parts).lower())


def _finding_panel(outcome: CheckOutcome, finding_id: str) -> str:
    params = (
        ", ".join(f"{html.escape(k)}={html.escape(v)}" for k, v in outcome.params_used.items())
        or "None recorded."
    )
    poam_uuid, poam_title = _poam_ref(outcome)
    evidence_bits = []
    for item in outcome.evidence:
        bit = html.escape(item.description)
        if item.href:
            bit += f" <code>{html.escape(item.href)}</code>"
        evidence_bits.append(f"<p>{bit}</p>")
    evidence = "".join(evidence_bits) or "<p>No file attached.</p>"
    return f"""
    <tr class="finding" id="{html.escape(finding_id)}" hidden>
      <td colspan="4">
        <div class="finding-list">
          <div class="finding-item">
            <span class="dot fail" aria-hidden="true"></span>
            <div>
              <h3>Finding</h3>
              <p>{html.escape(outcome.message)}</p>
            </div>
          </div>
          <div class="finding-item">
            <span class="dot" aria-hidden="true"></span>
            <div>
              <h3>Parameters</h3>
              <p>{params}</p>
            </div>
          </div>
          <div class="finding-item">
            <span class="dot" aria-hidden="true"></span>
            <div>
              <h3>POA&amp;M</h3>
              <p>{html.escape(poam_title)} — <code>{html.escape(poam_uuid)}</code></p>
            </div>
          </div>
          <div class="finding-item">
            <span class="dot" aria-hidden="true"></span>
            <div>
              <h3>Evidence</h3>
              {evidence}
            </div>
          </div>
        </div>
      </td>
    </tr>
    """


def _rows(run: AssessmentRun) -> str:
    chunks: list[str] = []
    for index, outcome in enumerate(run.outcomes):
        expandable = outcome.status in {"fail", "error"}
        finding_id = f"finding-{index}"
        expand = ""
        if expandable:
            expand = (
                f'<button type="button" class="expand" data-expand '
                f'aria-expanded="false" aria-controls="{finding_id}" '
                f'aria-label="Show finding for {html.escape(outcome.control_id)}">▸</button>'
            )
        chunks.append(
            f"""
            <tr class="check" data-status="{html.escape(outcome.status)}" data-search="{_search_blob(outcome)}">
              <td class="ctrl">{expand}<code>{html.escape(outcome.control_id)}</code></td>
              <td><code>{html.escape(outcome.rule_id)}</code></td>
              <td><span class="type">{html.escape(outcome.spec.check_type)}</span></td>
              <td><span class="pill {html.escape(outcome.status)}">{html.escape(HTML_STATUS[outcome.status])}</span></td>
            </tr>
            """
        )
        if expandable:
            chunks.append(_finding_panel(outcome, finding_id))
    return "".join(chunks)


def render_html(run: AssessmentRun, bundle: OscalBundle | None = None) -> str:
    del bundle  # control titles stay on the catalog; the table uses IDs from the run
    counts = run.counts()
    passed = counts["pass"]
    failed = counts["fail"] + counts["error"]
    manual = counts["not_automated"] + counts["needs_evidence"]
    automated = passed + failed
    rate = round(100 * passed / automated) if automated else 0
    rate_hint = (
        f"{passed} of {automated} automated checks"
        if automated
        else "No automated checks in this run"
    )
    from enact.writers import _now_iso

    generated = html.escape(_now_iso(run.ended))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="{report_csp()}">
  <title>{html.escape(run.title)}</title>
  {theme_bootstrap_script_tag()}
  <style>{theme_stylesheet()}{REPORT_CSS}</style>
</head>
<body>
  <div class="wrap">
    <div class="report-head">
      <div>
        <p class="kicker">Enact assessment</p>
        <h1>{html.escape(run.title)}</h1>
      </div>
      {theme_toggle_html()}
    </div>
    <p class="lede">Each row is a check. Pass and fail come from automation. Manual and not-checked controls still need a person — that is not a failure.</p>
    <div class="cards" aria-label="Result counts">
      <article class="card">
        <div class="card-top">
          <span class="label">Passed</span>
          <span class="pill pass">Passed</span>
        </div>
        <p class="count">{passed}</p>
        <div class="bar" role="progressbar" aria-label="Pass rate" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{rate}">
          <span style="width:{rate}%"></span>
        </div>
        <p class="hint">{rate}% pass rate · {html.escape(rate_hint)}</p>
      </article>
      <article class="card">
        <div class="card-top">
          <span class="label">Failed</span>
          <span class="pill fail">Failed</span>
        </div>
        <p class="count">{failed}</p>
        <p class="hint">Automated and hybrid failures become POA&amp;M items.</p>
      </article>
      <article class="card">
        <div class="card-top">
          <span class="label">Manual / Not checked</span>
          <span class="pill wait">Manual</span>
        </div>
        <p class="count">{manual}</p>
        <p class="hint">Recorded as observations, not as failures.</p>
      </article>
    </div>
    <div class="toolbar">
      <label class="visually-hidden" for="q" style="position:absolute;left:-9999px">Search controls</label>
      <input id="q" type="search" placeholder="Search control ID, rule ID, or message">
      <div class="filters" role="group" aria-label="Filter by status">
        <button type="button" data-filter="all" aria-pressed="true">All</button>
        <button type="button" data-filter="pass">Passed</button>
        <button type="button" data-filter="fail">Failed</button>
        <button type="button" data-filter="manual">Manual</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Control ID</th>
            <th>Rule ID</th>
            <th>Check type</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {_rows(run)}
        </tbody>
      </table>
      <p class="empty" id="empty" hidden>No checks match this search or filter.</p>
    </div>
    <footer class="note">
      Generated by Enact {html.escape(__version__)} at {generated}.
      Ran locally; nothing was sent off this machine.
    </footer>
  </div>
  <script>{theme_js()}{REPORT_JS}</script>
</body>
</html>
"""
