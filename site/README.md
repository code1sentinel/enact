# Enact in the browser

The Pages app at the site root is Enact: Catalog → Checks → Evidence → Run, with a vendored OPA WASM library.

Rebuild (OPA 1.8.x on `PATH`):

```bash
uv run python scripts/build_browser_app.py
```

Serve `site/` over http(s) and open `/`. Catalogs and evidence are opened with the File API in the tab; nothing is uploaded. Custom Rego stays on the Enact CLI. Notes: [docs/spikes/browser-opa.md](../../docs/spikes/browser-opa.md) (investigation history) and [ADR 0014](../../docs/adr/0014-browser-app-is-primary.md).
