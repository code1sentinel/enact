# Investigation: OPA / Rego in the browser

Date: 2026-10-05; updated 2026-10-06. Companion to [ADR 0013](../adr/0013-browser-only-guided-app.md), [ADR 0014](../adr/0014-browser-app-is-primary.md), and [PRD](../prds/browser-ui.md). The product host is the Pages app at `site/index.html`.

This file is investigation notes, not user-facing copy.

## What we tried

OPA’s documented browser path is **not** “run the `opa` binary in wasm.” It is:

1. **Compile** policies ahead of time with the 1.8.x CLI: `opa build -t wasm -e <slash/path>`.
2. **Evaluate** the resulting `policy.wasm` in the browser with OPA WASM ABI 1.2 (`opa_eval`).

The official JS SDK is [`@open-policy-agent/opa-wasm`](https://www.npmjs.com/package/@open-policy-agent/opa-wasm). It expects a precompiled module (or a bundle tarball). It can be loaded from unpkg; **we do not**. ADR 0013 forbids a CDN. We vendor a small loader instead of the npm package.

The 1.8.0 `opa_linux_amd64_static` binary we pin in CI reports `WebAssembly: unavailable` (it cannot *evaluate* wasm itself) but **`opa build -t wasm` works**. Output bundle `.manifest` includes `"rego_version": 1`.

## Mapping `enact run` → browser

`OpaEngine.run` builds `payload` / `oscal_params` / `check` (plus legacy keys). The browser runner in `site/enact.js` builds the same input document and calls `opa_eval` on a library entrypoint (`enact/login_lockout/result`, …).

Multiple `-e` flags share **one** `policy.wasm`. The automated starter library compiles into that module.

Builtins:

- Core arithmetic, `to_number`, `is_number`, JSON, comparisons: **native** in the module.
- `sprintf`: **host** builtin. Implemented in `site/opa-eval.js`.
- `http.send` and other I/O builtins: **must not** be implemented (privacy). Leave them throwing.

## Pages

`scripts/build_site.py` copies `site/` and rebuilds wasm via `scripts/build_browser_app.py`. CSP:

- `script-src 'self' <theme-bootstrap-hash> 'wasm-unsafe-eval'`
- `connect-src 'self'` — `fetch('./policy.wasm')` only. User files use FileReader.
- No `file://` guarantee: same-origin fetch needs http(s).

## Still on the CLI

1. **No in-browser Rego compiler.** User-edited policy and `enact checks draft` stay on localhost.
2. Full evidence-schema jsonschema validation (browser bind is field/type checks, not Draft 2020-12).
3. Large catalogs: `JSON.parse` of a full OSCAL catalog in a tab may hitch.

## Rebuild

```bash
uv run python scripts/build_browser_app.py
```

`opa build -t wasm` is **not bit-identical across machines**. Tests check that a rebuild evaluates the samples, not that bytes match the committed `policy.wasm`.
