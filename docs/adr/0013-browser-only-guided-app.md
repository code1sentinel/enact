# ADR 0013: Browser-only guided app (client-side OPA)

- Status: accepted (direction; product host is not this PR)
- Date: 2026-10-05
- PRD: [docs/prds/browser-ui.md](../prds/browser-ui.md)

## Context

`enact ui` already walks Catalog → Checks → Evidence → Run, but it is a Python process bound to `127.0.0.1`. Users must install Python, OPA, and the package. Andre’s product ask is that GRC reviewers should not need download, install, or localhost: the same stepper should run **fully in the browser**, evaluating OPA/Rego on the machine so catalogs and evidence never leave it.

ADR 0007 already forbids outbound product calls and forbids a hosted runner that accepts uploads. GitHub Pages is a static showcase. Any browser app has to keep that invariant, not punch a hole in it.

## Options considered

1. **Status quo — localhost Python UI.** Keep `enact ui` as the only guided path. It already satisfies privacy (nothing binds off-loopback; `/api/run` never leaves the box). It fails the “no install” bar.

2. **Hosted server with uploads.** A multi-tenant or Pages-adjacent backend receives catalogs and evidence, runs OPA, returns a report. **Rejected.** Catalogs and IAM dumps are the data ADR 0007 exists to protect. A server that accepts those files is a new product, a new threat model, and a new outbound path. Not in scope.

3. **Browser-only evaluator (OPA policy WASM / JS).** Pages (or any static host) ships HTML/JS plus a WebAssembly module produced by `opa build -t wasm` from Enact’s Rego. The browser loads the module **same-origin**, evaluates `input` in-process, and never POSTs user catalogs or evidence. Compilation of library checks happens in CI at site-build time, not on a user’s files.

## Decision

Pursue **option 3**. The privacy invariant holds: no server sees user catalogs or evidence; AI keys are still never written; no new product outbound that transmits those files. CDN loads of OPA WASM or the JS SDK are **not** allowed (that would be a third-party fetch of the engine, and a surprise network call). Vendor the compiled `policy.wasm` and a small same-origin loader.

`enact ui` stays until a browser app reaches parity (library, catalog mapping, evidence envelope, drafts, report, project zip). CI stays `enact run` on the CLI. GitHub Pages may ship a **static** client-side spike or later SPA; it still must not accept uploads to a server and must not present itself as a place to park secrets.

This ADR does **not** replace ADR 0004 (OPA remains the reference engine) or ADR 0007 (local-only). It says *where* OPA may run: in the browser, on a precompiled wasm module, with user data staying in that browser.

## Spike (this PR)

A hello-world lives at [site/browser-spike/](../../site/browser-spike/) (notes: [docs/spikes/browser-opa.md](../spikes/browser-opa.md)):

- `opa build -t wasm` on the library `ac-login-lockout` policy (Rego v1) produces ~140 KiB `policy.wasm`.
- A vendored JS loader implements OPA WASM ABI 1.2 `opa_eval` plus the one host builtin the library needs (`sprintf`).
- Passing and failing samples, shaped like the document `OpaEngine` feeds OPA, evaluate to pass/fail in the browser.
- `connect-src 'self'` loads the wasm from the same origin; no unpkg/CDN.

## Consequences

- **Easier:** GRC users can try a check without installing OPA. Pages can prove “OPA ran here” with sample data that already ships in the repo.
- **Harder:** Arbitrary user-edited or draft Rego cannot compile in the browser today. OPA’s wasm target is a *planned evaluation path for a precompiled policy*, not the `opa` CLI compiled to wasm. Custom policy remains a localhost/`enact run` path until a later ADR revisits in-browser compile (or we precompile only the library).
- **Off-limits:** Hosted upload APIs; CDN for the engine or SDK; implementing `http.send` in the JS host (would be a new outbound).
- **Next slice:** compile the whole automated library into one wasm (multiple `-e` entrypoints share one ~140 KiB module) and evaluate every pass/fail sample with the same input document `enact run` builds. See the PRD.
