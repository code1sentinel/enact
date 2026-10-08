# PRD: Fully client-side guided app (browser OPA)

- Status: shipped (primary path; this slice)
- Owner: Andre / GRC Engineering Club
- Date: 2026-10-06
- Related ADRs: [0004](../adr/0004-opa-reference-engine.md), [0007](../adr/0007-local-only-privacy-model.md), [0013](../adr/0013-browser-only-guided-app.md), [0014](../adr/0014-browser-app-is-primary.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

`enact ui` is a guided path, but it still requires a local install. Reviewers who are not allowed to install tooling — or who should not have to — cannot run Catalog → Checks → Evidence → Run at all. A hosted backend that accepted those files would violate the local-first promise.

## Goals

- A guided UI that runs **entirely in the browser**: Catalog → Checks → Evidence → Run, with OPA/Rego evaluation in-process (WebAssembly).
- **Privacy invariant:** user catalogs and evidence never leave the machine. No upload API. No new product outbound that transmits those files. AI keys are never written.
- Same check contract as `enact run`: Rego v1, `result.passed` / `result.message`, `input.payload` + `input.oscal_params` (+ `input.check` when present).
- GitHub Pages serves the app (HTML, JS, vendored wasm). It does not become a place to host user secrets.
- `enact ui` and `enact run` remain as **optional** localhost / CI paths.
- Call it **Enact**, not a spike.

## Non-goals

- GitHub Pages hosting of user catalogs, evidence, or reports that contain customer data.
- Removing or freezing `enact ui`.
- Replacing CI/`enact run` with a browser runner.
- A multi-tenant hosted OPA service, or any server that accepts uploads.
- Loading OPA or the JS SDK from a CDN (unpkg, jsDelivr, etc.).
- In-browser compilation of arbitrary/draft Rego (blocked today; say so in the app).
- Implementing OPA builtins that perform I/O (`http.send` and friends).

## Users and privacy

GRC reviewers and control owners. They pick a shipped sample or open a catalog/evidence file with the browser File API. Bytes stay in that tab. Same local-first model as ADR 0007, executed without a Python process.

**No new outbound network calls** that send user data. Same-origin `fetch` of vendored `policy.wasm` is allowed. Third-party hosts are not.

## Design references

Reuse Enact tokens (`site/theme.css`) and the `enact ui` pill stepper. Layout citations:

- Horizontal numbered stepper + Next: [Contra — Adding deliverables](https://mobbin.com/flows/ca8e2836-1501-484b-8af9-4eac3696700e)
- Guided progress checklist: [Vanta — Starter guide](https://mobbin.com/flows/81f0e7b6-ece8-4f14-8c2a-7bdbf8d045ce)
- Local file well + choose file: [Mistral AI — Upload Documents](https://mobbin.com/screens/77f399e9-65be-4bf0-9ae9-462c63a5f547), [Fiverr — Choose files](https://mobbin.com/screens/9feef30c-b0e1-4cde-ac17-6d149f641206)
- Results count cards after a run: [Codecademy — Completing an assessment](https://mobbin.com/flows/4a76a2f1-e45c-4d90-a3aa-a30debcc9f44)
- First-time walk-through polish: [first-time-walkthrough.md](first-time-walkthrough.md) (Twingate / Zoho / Vanta / Mixpanel / Supabase / Stripe / Square / Replit / Attio)

## Shape

Pages front door: Catalog → Checks → Evidence → Run. Bundled access-control sample, or local catalog JSON + evidence JSON via FileReader. Library automated/hybrid checks evaluate in one vendored wasm module. Download OSCAL assessment-results and the HTML report. One line: “Custom checks? Use the Enact CLI.”

## Slices

| # | Slice | Issue | Given / When / Then (summary) |
| --- | --- | --- | --- |
| 1 | ADR + PRD + wasm hello-world | #13 | Given the lockout samples, when the page evaluates, then pass/fail match with no third-party network. Shipped. |
| 2 | Library wasm + File API + OSCAL/HTML + Pages front door | this PR | Given the Pages app, when a newcomer uses the sample or local catalog+evidence, then they can run checks and download OSCAL without installing. |
| 3 | Draft / custom Rego in the tab | later | Blocked on an in-browser compiler. Stays on the CLI. |

### Slice 2 acceptance

- Given https://code1sentinel.github.io/enact/, when a newcomer lands, then they are in Catalog → Checks → Evidence → Run (not told to install first).
- Given the automated library, when CI compiles one wasm and the runner evaluates each pass/fail sample, then results match `OpaEngine`.
- Given the access-control example, when the browser writer emits assessment-results, then the JSON matches the Python writer (frozen clock) and validates against NIST 1.1.2.
- Given CSP, when inspected, then there is no CDN, `connect-src` is `'self'` or `'none'`, and user files are read with FileReader.
- Given `enact ui` and `enact run`, when this PR lands, then they still work and are documented as optional.

## Acceptance (feature-level)

- [x] Happy path: Catalog → Checks → Evidence → Run in the browser with library checks
- [x] Empty / error states a non-engineer can read
- [x] Tests for wasm evaluate + OSCAL golden vs Python + privacy
- [x] README + CHANGELOG
- [x] Pages app is the front door; still not a secrets host
- [x] Production UI cites Mobbin
- [x] Privacy review: no new third-party calls; no upload API

## Open questions

- In-browser compile of draft / user-edited Rego: wait for an OPA-as-wasm compiler, keep those paths on `enact ui`, or precompile-only forever? **This slice: keep on CLI.**
- Large catalogs: File API + JSON.parse memory limits in the tab.
- `wasm-unsafe-eval` in CSP (required to instantiate wasm).
