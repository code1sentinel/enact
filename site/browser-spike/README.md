# Browser OPA spike

Static hello-world: evaluate the lockout library check in the tab with vendored OPA WASM.

Rebuild (OPA 1.8.x on `PATH`):

```bash
uv run python scripts/build_browser_spike.py
```

Serve `site/` over http(s) and open `/browser-spike/`. Notes: [docs/spikes/browser-opa.md](../../docs/spikes/browser-opa.md). This is not `enact ui` and does not accept catalog uploads.
