# ADR 0007: Local-only privacy model

- Status: accepted
- Date: 2026-10-03
- PRD: [docs/prd.md](../prd.md)

## Context

Catalogs, IAM exports, and assessment results are sensitive. Codify’s local web app already commits to “nothing leaves the machine.” Enact is the sister tool; a phone-home, a hosted runner, or a third-party font/analytics call in the HTML report would break that story.

## Decision

Product code makes **no outbound network calls**. `enact run`, `enact serve`, and `enact ui` bind to localhost (`127.0.0.1`). Generated HTML is self-contained. The GitHub Pages site is a static host for the in-tab app (ADR 0014) plus sample reports; it does not accept uploads. CI may install OPA and Python packages — that is the maintainer pipeline, not the product.

A PR that adds a new third-party call (CDN, telemetry, hosted API) is rejected unless a new ADR explicitly allows it. The PR template has a privacy checkbox for this.

## Consequences

GRC users can run Enact on a catalog they are not allowed to ship off-box. We cannot offer a hosted multi-tenant runner without a new decision. Docs must keep saying user files never leave the tab.
