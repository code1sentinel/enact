# ADR 0014: Browser app is the primary Enact path

- Status: accepted
- Date: 2026-10-06
- PRD: [docs/prds/browser-ui.md](../prds/browser-ui.md), [docs/prds/ui-first.md](../prds/ui-first.md)

## Context

ADR 0013 chose a client-side OPA WASM evaluator so catalogs and evidence never leave the tab, and shipped a lockout hello-world under `site/browser-spike/`. Product direction from the owner: that path is the main use case; the CLI is optional; call it Enact, not a spike.

`enact ui` still requires a local Python + OPA install. CI still needs `enact run`. Neither goes away. What changes is the front door: a newcomer should open the Pages site and run Catalog → Checks → Evidence → Run without installing anything.

## Decision

The GitHub Pages app **is Enact**. It is the default onboarding path.

1. Visiting https://code1sentinel.github.io/enact/ opens the guided app (Catalog → Checks → Evidence → Run), not a “static demo” landing that tells people to install first.
2. User-facing copy says **Enact**. Do not call the app a spike, an OPA spike, or a browser-only path in progress.
3. Library automated/hybrid checks are compiled with `opa build -t wasm` (OPA 1.8.x, Rego v1) into one vendored `policy.wasm`. No CDN. User catalogs and evidence are opened with the File API (`FileReader`); they are never POSTed.
4. `enact ui` and `enact run` remain fully supported as **optional** localhost and CI paths. Custom / draft Rego stays there: there is no in-browser Rego compiler.
5. ADR 0007’s privacy invariant is unchanged: no upload host, no new product outbound that transmits catalogs or evidence, AI keys are never written. Same-origin fetch of vendored wasm is allowed (`connect-src 'self'`). User files do not use the network (`connect-src` is never widened for them).

This ADR does not replace ADR 0004 (OPA remains the reference engine) or ADR 0013 (browser evaluation is still precompiled wasm). It records that the spike graduated: the browser app is the product, not an experiment.

## Consequences

- **Easier:** GRC reviewers can run the bundled library (or their own catalog + evidence JSON) in a tab and download OSCAL assessment-results and the HTML report with no install.
- **Harder:** Arbitrary user-edited Rego still cannot compile in the browser. The app says so in one line: “Custom checks? Use the Enact CLI.”
- **Off-limits:** Hosted upload APIs; CDN for the engine; implementing `http.send` in the JS host.
- **Docs:** README, `--help` epilog, and Pages copy lead with the browser app; CLI/CI sit under “Optional: CLI and CI.” Sample reports from `examples/access-control/` stay reachable.
