# PRD: Evidence envelope + first-party adapters (samples first)

- Status: draft
- Owner: Andre (code1sentinel)
- Date: 2026-10-05
- Related ADRs: [0003](../adr/0003-no-c2p-runtime-dependency.md), [0004](../adr/0004-opa-reference-engine.md), [0007](../adr/0007-local-only-privacy-model.md), [0010 (proposed)](../adr/0010-evidence-envelope.md)
- Parent: [docs/prd.md](../prd.md)

## Problem

Every check reads its own ad hoc JSON. The only contract is a sample `template.json` and files in `examples/`. GRC users do **not** invent evidence standards — they upload whatever their tools export, or paste a sample. Asking them to design a schema is a dead end.

Without a shared shape:

- **CI wiring** guesses from a sample; a typo reaches OPA and fails confusingly (or a loose policy passes).
- **Assessors** cannot tell where input came from, when, or by what.
- **Collectors** (Terraform, cloud exports) each invent a shape, and Rego grows branches for every dump format.

Today the OPA adapter also merges the whole file into `input`, so policies couple to whatever the file happened to contain.

## Product stance (locked)

**Enact ships the standard. Users do not invent it.**

1. Enact owns `enact.*` payload types and sample envelopes.
2. **Adapters** turn common export formats into those envelopes. Users run an adapter on a dump they already have; they do not design schemas.
3. The UI/CLI path is: pick a check → download sample / run adapter → validate → run. Custom payload types are out of scope until adapters prove a gap.

## Goals

- One **evidence envelope**: metadata (who/what/when) + typed payload (`payload_type` + `payload_version`).
- **JSON Schema validation before OPA.** Invalid evidence → `error`, never `pass`.
- Rego reads **only** `input.payload` (plus `input.oscal_params`, `input.check`).
- Each library check declares the payload type/versions it accepts; templates are **generated from schema**.
- Provenance in OSCAL (id, type/version, `collected_at`, collector, payload SHA-256) — not the body.
- A **first-party adapter pack** for the most common sources GRC teams already export (see below). Adapters stay **outside** Enact core (no cloud SDKs, no outbound calls from `enact`).
- Versioning **fails closed**.

## Non-goals

- Asking users to define payload types or JSON Schema in v1.
- Shipping cloud collectors **inside** `src/enact/` (would pull SDKs/network into a local-only tool).
- Calling any cloud/SaaS API from Enact core (ADR 0007).
- Signing/attestations in v1 (`integrity` reserved).
- Storing raw evidence bodies in OSCAL.
- Replacing manual markdown evidence for manual checks.
- C2P as a dependency (ADR 0003) — related prior art only.

## Users and privacy

- **GRC engineer** — runs an adapter on an export, then `enact run`.
- **Non-terminal user** — downloads a sample or uploads adapter output on the Evidence step.
- **Assessor** — reads provenance on results.
- **Adapter maintainer** (us, later community) — maps a dump format → `enact.*` payload.

Rules: no new outbound calls from Enact; payload schemas settings-shaped where possible; `additionalProperties: false`; OSCAL gets hash not body; no credentials in envelopes; `subject.id` may be pseudonymous.

## Design references

v1 is CLI + adapters + engine. UI polish (upload errors, template download) needs **Mobbin refs before design** — later slice.

## Shape

```
common export dumps                 adapter pack (outside core)     Enact core (offline)
─────────────────────────           ───────────────────────────     ──────────────────────────────
terraform show -json ─────────────► enact-adapt terraform ──┐
aws iam get-account-password-policy ► enact-adapt aws-iam ──┤
aws organizations … SCP JSON ─────► enact-adapt aws-scp ────┼─► envelope bundle ─► validate ─► OPA
okta policy export JSON ──────────► enact-adapt okta ───────┤                      (input.payload)
hand / UI sample ─────────────────► (already an envelope) ──┘
```

Users never design the middle box. They pick a dump they already have.

### Envelope (sketch, `enact-evidence` 1.0)

```json
{
  "enact_evidence": "1.0",
  "id": "8f0c6a7e-2f5c-4b1e-9a3d-0c1f6c2b9e11",
  "collected_at": "2026-10-05T08:30:00Z",
  "collector": {
    "name": "enact-adapt-aws-iam",
    "version": "1.0",
    "kind": "adapter"
  },
  "subject": {
    "type": "cloud-account",
    "id": "prod-aws",
    "environment": "prod"
  },
  "source": {
    "system": "aws-iam",
    "ref": "exports/password-policy.json"
  },
  "payload_type": "enact.iam.account-policy",
  "payload_version": "1.0",
  "payload": {
    "lockout_threshold": 5,
    "mfa_required": true,
    "password_min_length": 14
  },
  "labels": { "ticket": "GRC-142" }
}
```

| Field | Req | Notes |
| --- | --- | --- |
| `enact_evidence` | yes | Envelope version. Unknown → error. |
| `id` | yes | Stable id for OSCAL reference. |
| `collected_at` | yes | When the **source** was collected, not run time. |
| `collector` | yes | `kind`: `manual` \| `adapter` \| `sample` \| `legacy`. |
| `subject` | yes | What the evidence is about. |
| `source` | no | Local path / opaque id — never a URL Enact fetches. |
| `payload_type` / `payload_version` / `payload` | yes | Validated against vendored schemas. |
| `labels` / `integrity` | no | Labels not read by Rego; integrity reserved. |

### Bundle

```json
{
  "enact_evidence_bundle": "1.0",
  "items": [ { "...envelope..." } ]
}
```

Bare single envelope OK. v1: **at most one envelope per `payload_type`** per bundle.

### Payload types for v1 (from today's library)

| `payload_type` | Checks |
| --- | --- |
| `enact.iam.account-policy` 1.0 | ac-account-review, ac-login-lockout, ac-privileged-review, ac-inactive-disable, ac-mfa-enforced, ac-password-length |
| `enact.logging.audit` 1.0 | au-logging-enabled, au-log-retention |
| `enact.crypto.posture` 1.0 | sc-encryption-at-rest, sc-encryption-in-transit |

Fields optional at schema level; each check lists `payload_requires`. Missing required field → `error`, not `fail`.

### First-party adapters (most frequent sources)

Ship as a small **adapter pack** outside core (proposed home: `contrib/adapters/` in-repo for docs+scripts, or companion CLI `enact-adapt` — open question). Each adapter: read a dump file → write a bundle → exit 0 only if `enact evidence validate` would pass.

| Priority | Adapter | Input (what users already have) | Emits |
| --- | --- | --- | --- |
| P0 | **sample / template** | none — generated from schema | `collector.kind=sample` envelope |
| P0 | **manual form → envelope** | UI / CLI filled fields | `kind=manual` |
| P1 | **aws-iam-password-policy** | `aws iam get-account-password-policy` JSON | `enact.iam.account-policy` |
| P1 | **terraform-plan** | `terraform show -json` (or plan file) | IAM + logging + crypto fields it can map |
| P1 | **aws-scp** | Organizations SCP / policy document JSON | IAM-relevant statements mapped into account-policy / labels; unmappable → clear skip report |
| P2 | **okta-password-policy** | Okta policy export JSON | `enact.iam.account-policy` |
| P2 | **aws-cloudtrail / logging** | Trail / logging config JSON export | `enact.logging.audit` |
| P2 | **aws-s3-encryption / kms** | Bucket encryption / KMS key policy snippets | `enact.crypto.posture` |
| P3 | **azure-ad-password** / **entra** | Graph/portal export JSON | `enact.iam.account-policy` |
| P3 | **gcp-org-policy** | Org policy export | mapped `enact.*` fields |

v1 build order: P0 with schema slices, then **P1 trio** (aws-iam, terraform-plan, aws-scp) — covers most cloud GRC demos for current library checks. P2/P3 after those land.

Adapter rules:

- Map **into** `enact.*` types only. No user-defined types in v1.
- Never call cloud APIs from the adapter pack in CI by default — take a **file path**. (Optional later: thin wrappers that shell out to `aws`/`terraform` the user already has.)
- Print a short mapping report: which fields filled, which left empty, which source keys ignored.
- Fail closed on unparseable input; never emit a half-valid envelope that would pass schema by accident with empty payload.

### Check declaration

```json
{
  "rule_id": "ac-login-lockout",
  "payload_type": "enact.iam.account-policy",
  "payload_versions": ["1.0"],
  "payload_requires": ["lockout_threshold"]
}
```

### OPA input

```json
{
  "payload": { "lockout_threshold": 5 },
  "oscal_params": { "c-ac-7_prm_1": "5" },
  "check": { "rule_id": "ac-login-lockout", "control_id": "c-ac-7", "ksi_id": "KSI-IAM-AAM" }
}
```

```rego
configured := input.payload.lockout_threshold
```

### CLI

```bash
enact evidence validate --input evidence.json
enact evidence template --check ac-login-lockout
enact evidence types
enact run ... --input evidence.json

# adapter pack (outside core — names illustrative)
enact-adapt aws-iam --in password-policy.json --out evidence.json
enact-adapt terraform --in plan.json --out evidence.json
enact-adapt aws-scp --in scp.json --out evidence.json
```

## Boundary

| Layer | Owns |
| --- | --- |
| **Enact core** | envelope + `enact.*` schemas, validate, OPA shaping, OSCAL provenance, samples/templates |
| **Adapter pack** | dump → envelope; mapping docs; fixture dumps in tests |
| **User** | runs export tools they already use; never designs schema |

Contract between adapter and core: **the file**. Done when `enact evidence validate` passes.

## Versioning

- Envelope and payload types versioned `MAJOR.MINOR`; unknown → error.
- Schemas immutable once released; change = new version file.
- Bare legacy JSON: still runs in v1 with deprecation notice (`collector.kind=legacy`); removal timing open.

## Slices

| # | Slice | Summary |
| --- | --- | --- |
| 1 | Thin v1 core | Envelope 1.0 + `enact.iam.account-policy`; `enact evidence validate`; two IAM checks on `input.payload`; provenance; legacy notice |
| 2 | Library migrate | Remaining checks + logging/crypto types; examples as bundles |
| 3 | Templates | `evidence template` / `types`; schema-generated samples |
| 4 | **P1 adapters** | aws-iam-password-policy, terraform-plan, aws-scp + fixtures + mapping docs — in progress (`contrib/adapters/`, `enact-adapt`) |
| 5 | UI Evidence step | validate on upload, field errors, download sample (Mobbin first) |
| 6 | P2 adapters | okta, aws logging, aws encryption |

## Acceptance (Given / When / Then)

1. **Sample path.** Given I run `enact evidence template --check ac-login-lockout`, when I validate and run, then the check can pass and observation has evidence props.
2. **Adapter path.** Given a fixture AWS password-policy JSON, when `enact-adapt aws-iam` runs, then output validates and `ac-password-length` / lockout checks get the mapped fields.
3. **Typo stops before OPA.** Given `lockout_treshold`, when validate/run, then field-path error; never `pass`.
4. **Unknown versions fail closed.**
5. **Check/version mismatch → error.**
6. **Missing required field → error** (not fail).
7. **Missing payload type → error.**
8. **Duplicate type in bundle → error.**
9. **Rego sees only payload, oscal_params, check.**
10. **No network** (no remote `$ref`).
11. **Legacy still runs (v1)** with one deprecation notice.
12. **No payload body in OSCAL** (hash + metadata only).
13. **OSCAL still validates** (NIST 1.1.2).
14. **Adapter mapping report** lists filled / empty / ignored keys for the P1 adapters.

## Acceptance (feature-level)

- [ ] Happy paths: sample + at least one P1 adapter
- [ ] Readable evidence errors
- [ ] Tests (failing first) + OSCAL schema validation
- [ ] README / CHANGELOG / adapter mapping docs
- [ ] Pages demo examples updated with envelopes
- [ ] UI slice cites Mobbin
- [ ] Privacy: no outbound from core; adapters file-in/file-out by default

## Open questions

1. **Legacy removal.** How long does bare JSON keep working?
2. **POA&M for evidence errors.** Keep today's exit 1 + POA&M, or exclude `evidence:` errors from POA&M (maybe exit 2)?
3. **Custom payload types.** Confirm **out of v1** (only `enact.*` + adapters)?
4. **Adapter pack home.** **Decided (slice 4 / ADR 0011):** `contrib/adapters/` in this repo plus an `enact-adapt` console script. Not a separate repo; not inside `src/enact/`.
5. **Freshness.** Warn/fail on old `collected_at`, or ignore for now?
6. **Multi-account subjects.** Needed soon, or stick to one-per-type in v1?
7. **Payload granularity.** Keep one type per domain (current draft)?
8. **Report detail.** Show payload values in HTML, or policy message only?
9. **Envelope `id`.** Required UUID vs any stable string?
10. **P1 adapter set.** Confirm aws-iam + terraform-plan + aws-scp as the first trio, or swap any (e.g. Okta before SCP)?
