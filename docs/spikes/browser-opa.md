# Spike: OPA / Rego in the browser

Date: 2026-10-05. Companion to [ADR 0013](../adr/0013-browser-only-guided-app.md) and [PRD](../prds/browser-ui.md). Runnable proof: [site/browser-spike/](../../site/browser-spike/).

This is an investigation, not the product host.

## What we tried

OPA’s documented browser path is **not** “run the `opa` binary in wasm.” It is:

1. **Compile** policies ahead of time with the 1.8.x CLI: `opa build -t wasm -e <slash/path>`.
2. **Evaluate** the resulting `policy.wasm` in the browser with OPA WASM ABI 1.2 (`opa_eval`).

The official JS SDK is [`@open-policy-agent/opa-wasm`](https://www.npmjs.com/package/@open-policy-agent/opa-wasm). It expects a precompiled module (or a bundle tarball). It can be loaded from unpkg; **we do not**. ADR 0013 forbids a CDN. This spike vendors a ~100-line loader instead of the npm package (jszip + extra builtins we do not need yet).

The 1.8.0 `opa_linux_amd64_static` binary we pin in CI reports `WebAssembly: unavailable` (it cannot *evaluate* wasm itself) but **`opa build -t wasm` works**. Output bundle `.manifest` includes `"rego_version": 1`.

## Mapping `enact run` → browser

`OpaEngine.run` ([src/enact/engines.py](../../src/enact/engines.py)):

1. Read `spec.policy` from disk.
2. Bind evidence (`input.payload` from envelope or legacy `iam` / `payload`).
3. Build the input document: `payload`, `oscal_params`, `check`, plus legacy keys.
4. `opa eval --format json --data policy.rego --input input.json data.<package>.result`.
5. Interpret `result.passed` (or `allow`) and `message`.

The browser path for **library** checks:

1. CI runs `opa build -t wasm -e enact/login_lockout/result` (slash path, not dotted).
2. The page fetches same-origin `policy.wasm` (no user files on the wire).
3. JS builds the same input document and calls `opa_eval`.
4. The same `passed` / `message` object comes back.

Catalog load, manifest merge, evidence-schema validation, drafts, and OSCAL writers are still Python. They are not in this spike.

## Sizes and builtins

| Artifact | Size (OPA 1.8.0) |
| --- | --- |
| `ac-login-lockout` `policy.wasm` | ~141 KiB |
| Two checks, two `-e` entrypoints, one module | ~142 KiB |

Multiple `-e` flags share **one** `policy.wasm` with an entrypoint map (`entrypoints()` export). The next slice should compile the whole automated library into that one module rather than one wasm per check.

Builtins:

- Core arithmetic, `to_number`, `is_number`, JSON, comparisons: **native** in the module.
- `sprintf`: **host** builtin (`builtins()` → `{"sprintf": 3}` on the lockout policy). The spike implements it in JS.
- `http.send` and other I/O builtins: **must not** be implemented (privacy). Leave them throwing.

The current library policies all use `sprintf` in `result.message`. A loader without that host function cannot evaluate them.

## Pages as a static SPA

`scripts/build_site.py` already copies `site/` recursively. Putting the spike under `site/browser-spike/` means GitHub Pages will publish it at `/enact/browser-spike/` with no extra host. The wasm is a static file. CSP:

- `script-src 'self' <theme-bootstrap-hash> 'wasm-unsafe-eval'` — Chrome/Firefox require `'wasm-unsafe-eval'` to instantiate wasm (this is not `unsafe-eval` for JS).
- `connect-src 'self'` — `fetch('./policy.wasm')` only. No third-party.
- No `file://` guarantee: same-origin fetch needs http(s). Serve `site/` or use the Pages URL.

## Blockers (not this PR)

1. **No in-browser Rego compiler.** User-edited policy in `enact ui` and `enact checks draft` cannot become wasm without a compile step. Options for a later ADR: precompile library only; compile OPA itself to wasm (large, unproven here); keep custom Rego on localhost.
2. **Porting the rest of the runner.** Evidence bind, catalog inspect, writers, draft generation — Python today. A JS port or an Enact-in-wasm is a product slice, not a one-file spike.
3. **Large catalogs.** `JSON.parse` of a full OSCAL catalog in a tab may hitch; measure before promising.
4. **File API UX** for evidence/catalogs needs Mobbin before it is product chrome.
5. **SDK vs loader.** If later checks need more host builtins, vendor a **pinned** `@open-policy-agent/opa-wasm` into the repo (still no CDN) rather than growing `opa-eval.js` ad hoc.

## Rebuild

```bash
uv run python scripts/build_browser_spike.py
```

`opa build -t wasm` is **not bit-identical across machines** (name-section layout / clang producer strings differ). Tests check that a rebuild evaluates the samples, not that bytes match the committed `policy.wasm`. Pages rebuilds wasm in `scripts/build_site.py`.
