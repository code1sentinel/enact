# Adapter pack (outside Enact core)

First-party adapters turn dumps GRC teams already have into Enact evidence envelopes.
They are **not** part of `src/enact/` (ADR 0007: no cloud SDKs, no outbound calls from the CLI).

Contract: file in, envelope or bundle out. Done when `enact evidence validate --input` exits 0.

## Planned P1 trio

| Adapter | Input (what users already export) | Emits |
| --- | --- | --- |
| aws-iam-password-policy | `aws iam get-account-password-policy` JSON | `enact.iam.account-policy` |
| terraform-plan | `terraform show -json` (or a plan file) | IAM fields the plan can map |
| aws-scp | Organizations SCP / policy document JSON | IAM-relevant statements mapped into account-policy |

Later: Okta password policy, CloudTrail/logging, S3/KMS encryption (see [docs/prds/evidence-schema.md](../../docs/prds/evidence-schema.md)).

This directory is a stub in slice 1. Adapter scripts land in a later slice.
