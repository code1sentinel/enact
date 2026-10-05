# Adapter pack (outside Enact core)

First-party adapters turn dumps GRC teams already have into Enact evidence envelopes.
They are **not** part of `src/enact/` (ADR 0007: no cloud SDKs, no outbound calls from the CLI; [ADR 0011](../../docs/adr/0011-adapter-pack-in-contrib.md)).

Contract: file in, envelope out. Done when `enact evidence validate --input` exits 0.

Adapters never call AWS, Terraform, or any other API. You export the dump yourself, then point `enact-adapt` at the file.

## Install / run

From a checkout with Enact installed (`uv sync --extra dev` or `pip install -e ".[dev]"`):

```bash
enact-adapt aws-iam --in password-policy.json --out evidence.json
enact-adapt terraform --in plan.json --out evidence.json
enact-adapt aws-scp --in scp.json --out evidence.json

enact evidence validate --input evidence.json
```

Equivalent without the console script:

```bash
PYTHONPATH=contrib/adapters python -m enact_adapt aws-iam --in password-policy.json --out evidence.json
```

A mapping report (filled / empty / ignored / skipped) is printed to stderr. The envelope is written only if at least one payload field mapped and `enact evidence validate` would pass. Unparseable or unmappable dumps exit 1 and do **not** write an empty payload.

Optional flags: `--collected-at`, `--subject-id`, `--subject-type`, `--environment`, `--id`.

Command aliases: `aws-iam-password-policy`, `terraform-plan`.

## P1 trio

| Adapter | Input (what users already export) | Emits | Mapping |
| --- | --- | --- | --- |
| `aws-iam` | `aws iam get-account-password-policy` JSON | `enact.iam.account-policy` | [mapping/aws-iam-password-policy.md](mapping/aws-iam-password-policy.md) |
| `terraform` | `terraform show -json` (or a plan file) | IAM fields the plan can map | [mapping/terraform-plan.md](mapping/terraform-plan.md) |
| `aws-scp` | Organizations SCP / policy document JSON | IAM-relevant statements mapped into account-policy | [mapping/aws-scp.md](mapping/aws-scp.md) |

Logging and crypto payload types are **not** emitted in this slice (`enact.logging.audit` / `enact.crypto.posture` are not on `main` yet). The terraform adapter reports those resources as skipped domains.

Later: Okta password policy, CloudTrail/logging, S3/KMS encryption (see [docs/prds/evidence-schema.md](../../docs/prds/evidence-schema.md)).

## Fixtures

Dumps under [fixtures/](fixtures/) are used by `tests/test_adapters.py`. They contain no credentials.
