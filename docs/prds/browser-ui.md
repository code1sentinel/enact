# PRD: Fully client-side guided app (browser OPA)

- Status: in progress (spike)
- Owner: Andre / GRC Engineering Club
- Date: 2026-10-05
- Related ADRs: [0004](../adr/0004-opa-reference-engine.md), [0007](../adr/0007-local-only-privacy-model.md), [0013](../adr/0013-browser-only-guided-app.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

`enact ui` is the guided path for people who are not comfortable in a terminal, but it still requires a local install (Python, OPA 1.8.x, the package) and a loopback server. Reviewers who are not allowed to install tooling — or who should not have to — cannot run Catalog → Checks → Evidence → Run at all. A hosted backend that accepted those files would violate the local-first promise.

## Goals

- A guided UI that runs **entirely in the browser**: Catalog → Checks → Evidence → Run, with OPA/Rego evaluation in-process (WebAssembly).
- **Privacy invariant:** user catalogs and evidence never leave the machine. No upload API. No new product outbound that transmits those files. AI keys are never written.
- Same check contract as `enact run`: Rego v1, `result.passed` / `result.message`, `input.payload` + `input.oscal_params` (+ `input.check` when present).
- GitHub Pages may serve the static assets (HTML, JS, vendored wasm). It does not become a place to host user secrets.
- `enact ui` remains until this UI reaches parity. CI remains the CLI.

## Non-goals

- GitHub Pages hosting of user catalogs, evidence, or reports that contain customer data.
- Removing or freezing `enact ui`.
- Replacing CI/`enact run` with a browser runner.
- A multi-tenant hosted OPA service, or any server that accepts uploads.
- Loading OPA or the JS SDK from a CDN (unpkg, jsDelivr, etc.).
- Production visual design of the stepper in this spike. **Mobbin citations are required before any product chrome** (the Catalog → Checks → Evidence → Run shell). This slice is an ADR + functional wasm hello-world only.
- In-browser compilation of arbitrary/draft Rego (blocked today; see risks).
- Implementing OPA builtins that perform I/O (`http.send` and friends).

## Users and privacy

GRC reviewers and control owners. They may pick a shipped sample or, later, open a catalog/evidence file with the browser File API. Bytes stay in that tab. Same local-first model as ADR 0007, executed without a Python process.

**No new outbound network calls** that send user data. Same-origin `fetch` of vendored `policy.wasm` is allowed. Third-party hosts are not.

## Design references

N/A for this slice — spike proof-of-concept and docs only; not production UI chrome.

Before slice 3+ (visible stepper, file pickers, report layout) stop and collect [Mobbin](https://mobbin.com) links. Do not invent a look. Reuse existing Enact tokens (`site/theme.css`) until those citations exist.

## Shape

Today (spike): a static page under `site/browser-spike/` loads the lockout library policy as wasm, evaluates the passing and failing samples, and shows pass/fail plus the Rego `message`. It reuses landing theme tokens. It is labelled as a spike, not the guided app.

Target (later slices): the same four steps as `enact ui`, implemented with File API + precompiled library wasm (and, if a later ADR allows, an in-browser compiler for custom Rego). Report rendering can reuse the HTML writer once a JS or wasm port exists, or emit a thinner in-tab result until then.

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | ADR + PRD + wasm hello-world | this PR | Given the spike page and the lockout samples, when the page evaluates in the browser (or the CI wasm loader), then the passing sample passes and the failing sample fails, with no third-party network. |
| 2 | **Next: library wasm runner** | not opened | Given the automated library checks, when CI compiles them to one wasm module and the runner evaluates each pass/fail sample with the `OpaEngine` input document, then results match `enact run` / `OpaEngine`. |
| 3 | Catalog File API | later | Given a local OSCAL catalog file, when the user opens it in the tab, then controls are listed without uploading. Needs Mobbin before chrome. |
| 4 | Stepper + evidence + report | later | Given selected library checks and local evidence, when Run is clicked, then pass/fail (and later OSCAL/HTML) render in-tab. Needs Mobbin. `enact ui` still ships. |

### Slice 1 acceptance (this PR)

- Given `docs/adr/0013-browser-only-guided-app.md` and `docs/prds/browser-ui.md`, when a reviewer reads them, then localhost UI, hosted uploads, and browser-only wasm are compared, and hosted uploads are rejected for privacy.
- Given `site/browser-spike/` and the lockout policy compiled with OPA 1.8 `opa build -t wasm`, when the passing sample is evaluated, then `result.passed` is true; when the failing sample is evaluated, then `result.passed` is false.
- Given the spike HTML, when CSP and script URLs are inspected, then there is no CDN, `connect-src` is `'self'` or tighter, and user catalogs are not posted anywhere.
- Given `enact ui`, when this PR lands, then the localhost app is still present and documented.

## Acceptance (feature-level)

- [ ] Happy path: Catalog → Checks → Evidence → Run in the browser with library checks (not this PR)
- [ ] Empty / error states a non-engineer can read
- [x] Tests for the spike wasm evaluate + privacy checks (this PR)
- [ ] README + CHANGELOG (CHANGELOG in this PR; README notes the spike)
- [ ] Pages demo copies `site/browser-spike/` (static); still not a secrets host
- [ ] Production UI slices cite Mobbin (not this spike)
- [x] Privacy review: no new third-party calls; no upload API

## Open questions

- In-browser compile of draft / user-edited Rego: wait for an OPA-as-wasm compiler, keep those paths on `enact ui`, or precompile-only forever?
- How much of `enact.oscal_io` / writers to port to JS vs calling into a future wasm of Enact itself?
- Large catalogs: File API + JSON.parse memory limits in the tab.
- `wasm-unsafe-eval` in CSP (required to instantiate wasm). Acceptable for Pages spike; revisit for a locked-down enterprise CSP.
