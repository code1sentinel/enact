# Privacy and security

Enact is local-first. Product code makes **no outbound network calls**. Catalogs, evidence, and results stay on the machine that opened them.

## In the browser

The hosted app at [https://code1sentinel.github.io/enact/](https://code1sentinel.github.io/enact/) evaluates in the tab.

- Files are opened with the browser file picker (`FileReader`). They are never POSTed.
- The only same-origin fetch is the vendored `policy.wasm` engine. No CDN for OPA, fonts, or analytics.
- The site does not accept uploads.
- Light / Dark / System is stored in `localStorage` (`enact-theme`) and never leaves the browser.

GitHub Pages is a static host for the app plus sample reports generated in CI. It is not a secrets host.

## On the CLI

- `enact ui` and `enact serve` bind `127.0.0.1` only.
- Adapters (`enact-adapt`) are file-in / file-out. They do not call AWS, Terraform, or any other API.
- Nothing under `src/enact/` includes a cloud SDK.

## What we do not do

- Host a runner that accepts your catalogs or evidence.
- Load the engine, SDK, fonts, or analytics from a third-party CDN.
- Write AI keys into source, fixtures, reports, HTML, env samples, or logs.

A new third-party call needs its own architecture decision record that explicitly allows it. The pull request template has a privacy checkbox for this.

See [ADR 0007](https://github.com/code1sentinel/enact/blob/main/docs/adr/0007-local-only-privacy-model.md) and [ADR 0014](https://github.com/code1sentinel/enact/blob/main/docs/adr/0014-browser-app-is-primary.md).
