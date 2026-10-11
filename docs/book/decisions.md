# Decision records

Architecture decisions live in [`docs/adr/`](https://github.com/code1sentinel/enact/tree/main/docs/adr) on GitHub. New records start from the [ADR template](https://github.com/code1sentinel/enact/blob/main/docs/templates/adr-template.md) and take the next free number.

| ADR | Summary | Status |
| --- | --- | --- |
| [0001](https://github.com/code1sentinel/enact/blob/main/docs/adr/0001-record-architecture-decisions.md) | Record load-bearing choices in numbered ADRs instead of README prose. | accepted |
| [0002](https://github.com/code1sentinel/enact/blob/main/docs/adr/0002-oscal-1-1-2-vendored-nist-schemas.md) | Vendor NIST OSCAL 1.1.2 schemas; do not depend on trestle (which targets 1.2.1). | accepted |
| [0003](https://github.com/code1sentinel/enact/blob/main/docs/adr/0003-no-c2p-runtime-dependency.md) | Reuse C2P mapping ideas; do not take a compliance-to-policy runtime dependency. | accepted |
| [0004](https://github.com/code1sentinel/enact/blob/main/docs/adr/0004-opa-reference-engine.md) | OPA/Rego v1 is the reference engine; other engines are reserved stubs. | accepted |
| [0005](https://github.com/code1sentinel/enact/blob/main/docs/adr/0005-pluggable-writers-fedramp-sdr-reserved.md) | Ship oscal, poam, markdown, html writers; reserve `fedramp-sdr`. | accepted |
| [0006](https://github.com/code1sentinel/enact/blob/main/docs/adr/0006-github-is-the-source-of-truth.md) | GitHub (`code1sentinel/enact`) is the source of truth; Origin is legacy. | accepted |
| [0007](https://github.com/code1sentinel/enact/blob/main/docs/adr/0007-local-only-privacy-model.md) | Product code makes no outbound calls; servers bind localhost. | accepted |
| [0008](https://github.com/code1sentinel/enact/blob/main/docs/adr/0008-css-theme-tokens.md) | Shared CSS tokens and a System-first Light/Dark toggle; no remote fonts. | accepted |
| [0009](https://github.com/code1sentinel/enact/blob/main/docs/adr/0009-draft-rego-checks.md) | Template-only draft Rego for unmatched controls; review is explicit. | accepted |
| [0010](https://github.com/code1sentinel/enact/blob/main/docs/adr/0010-evidence-envelope.md) | Shared evidence envelope, validated before OPA; users do not invent payload types. | proposed |
| [0011](https://github.com/code1sentinel/enact/blob/main/docs/adr/0011-adapter-pack-in-contrib.md) | First-party adapters live in `contrib/adapters/`, not `src/enact/`. | accepted |
| [0012](https://github.com/code1sentinel/enact/blob/main/docs/adr/0012-checks-json-user-facing-name.md) | User-facing mapping file is `checks.json` / `--checks`. | accepted |
| [0013](https://github.com/code1sentinel/enact/blob/main/docs/adr/0013-browser-only-guided-app.md) | Client-side OPA WASM evaluator; no hosted upload server. | accepted |
| [0014](https://github.com/code1sentinel/enact/blob/main/docs/adr/0014-browser-app-is-primary.md) | The GitHub Pages app is the primary Enact path; CLI is optional. | accepted |
| [0015](https://github.com/code1sentinel/enact/blob/main/docs/adr/0015-oscal-component-definition-mapping.md) | Component Definition is the OSCAL interchange mapping (C2P `Rule_Id` / `Check_Id`). | accepted |
| [0016](https://github.com/code1sentinel/enact/blob/main/docs/adr/0016-agent-skills-progressive-disclosure.md) | Short `AGENTS.md` plus vendored TDD / diagnosis / review skills. | accepted |

ADR 0013’s wasm evaluation path still stands; product stance was updated by 0014.
