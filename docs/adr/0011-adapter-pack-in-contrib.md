# ADR 0011: First-party adapter pack lives in contrib/, not src/enact

- Status: accepted
- Date: 2026-10-05
- PRD: [docs/prds/evidence-schema.md](../prds/evidence-schema.md) (slice 4)

## Context

Slice 1 shipped the evidence envelope and left an adapter stub. ADR 0010 says adapters turn common dumps into `enact.*` envelopes and must stay outside Enact core (no cloud SDKs, no outbound calls from `src/enact/`). Open question: in-repo `contrib/adapters/`, a separate `enact-adapt` repo, or both.

## Decision

Ship the P1 trio **in this repo** under `contrib/adapters/`:

- Python package `enact_adapt` (not under `src/enact/`)
- Console script `enact-adapt` (`aws-iam`, `terraform`, `aws-scp`)
- Fixtures and mapping docs next to the code
- Tests in `tests/test_adapters.py` that import the contrib package and assert `enact evidence validate`

Adapters read a local file and write a local envelope. They may import `enact.evidence` to honor the validate contract. They do not call AWS, Terraform, or any network API.

## Consequences

Easier: one PR can land adapters, fixtures, and CI; GRC users clone Enact and run `enact-adapt` without a second package.

Harder: the wheel includes `enact_adapt` via hatch `force-include` so the console script resolves; contributors must not add boto3/terraform providers to `src/enact/` or to the adapter pack.

Rejected alternatives:

- **Separate enact-adapt repo.** Extra release surface for three file-in/file-out scripts.
- **Adapters inside `src/enact/`.** Pulls collector code into the local-only CLI (ADR 0007 / 0010).
- **Shell-out to `aws`/`terraform` by default.** CI would need credentials or live APIs; file-in is the v1 contract.
