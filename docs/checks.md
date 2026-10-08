# checks.json convention

Enact maps OSCAL controls to runnable checks with a small JSON document, an
OSCAL Component Definition (C2P `Rule_Id` / `Check_Id` shape), or the same
fields stored as OSCAL props.

The user-facing file is **`checks.json`**. Pass it as `--checks`. `--manifest`
(and `-m`) still work as a deprecated alias.

Parameters are **not** duplicated here. The file names the OSCAL param
ids; Enact reads the values from the catalog, profile `set-parameters`, or
component-definition `set-parameters`.

## JSON

```json
{
  "schema_version": "1.0",
  "title": "Access-control checks",
  "checks": [
    {
      "rule_id": "ac-login-lockout",
      "control_id": "c-ac-7",
      "check_type": "automated",
      "engine": "opa",
      "policy": "policies/login_lockout.rego",
      "params": ["c-ac-7_prm_1"],
      "ksi_id": "KSI-IAM-AAM",
      "title": "Login lockout threshold"
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `rule_id` | yes | Stable id for the check implementation (the Rego package, InSpec profile, …). |
| `control_id` | yes | OSCAL control id. Every result is traced to this. |
| `check_type` | yes | `automated`, `manual`, or `hybrid`. |
| `engine` | automated/hybrid | `opa` in v1. `inspec`, `checkov`, and `cloud-config` are reserved. |
| `policy` | automated/hybrid | Path to the policy file, relative to `--workdir`. |
| `query` | no | OPA query. Default: `data.<package>.result`. |
| `params` | no | OSCAL param ids whose values are injected as `input.oscal_params`. |
| `ksi_id` | no | FedRAMP 20x Key Security Indicator id. Stored on observations; unused in v1 writers. |
| `payload_type` | automated (migrating) | Enact-owned evidence type, e.g. `enact.iam.account-policy`. |
| `payload_versions` | with `payload_type` | Accepted payload schema versions. Unknown versions fail closed. |
| `payload_requires` | with `payload_type` | Payload fields that must be present. Missing → `error`, not `fail`. |
| `evidence` | no | Path to supporting evidence linked from the report. |
| `evidence_needed` | manual/hybrid | What a person must still provide. |
| `review_status` | draft checks | `draft` until `enact checks review`. Draft results never count as passed. |

The JSON Schema is [`schemas/check-manifest.schema.json`](../schemas/check-manifest.schema.json).
Evidence envelopes use [`schemas/evidence/`](../schemas/evidence/).

## Rule ID

Use a lowercase, hyphenated id that names the *check*, not the engine:

- `ac-login-lockout`
- `ac-account-review`

Do not encode the control catalog version in the rule id. The control id
already does that. The same rule can satisfy more than one control by
repeating the row with a different `control_id`.

C2P-style `Rule_Id` / `Check_Id` props are accepted as aliases when
checks.json is derived from OSCAL. A full Component Definition is the
**interchange** mapping ([ADR 0015](adr/0015-oscal-component-definition-mapping.md)):
a `service` component binds controls to `Rule_Id`, a `validation` component
titled `OPA` binds `Rule_Id` to `Check_Id`, and parameters live as
`Parameter_Id` plus `set-parameters`. `checks.json` stays the authoring file.

```
enact emit-component-definition --checks checks.json --oscal catalog.json -O component-definition.json
enact run --oscal catalog.json --oscal component-definition.json --input evidence.json --workdir . --out out
```

## Parameters

Codify writes placeholders as OSCAL `params` and `{{ insert: param, <id> }}`
in the statement. Enact looks up `<id>` and passes `{ "<id>": "<value>" }`
into the engine. A lockout of `[5]` in the catalog is the same `5` the
Rego policy compares against. Change the catalog (or a profile
`set-parameters` overlay); do not edit the check.

## Check types

| Type | When the engine runs | Result if there is no human evidence |
| --- | --- | --- |
| `automated` | always | `pass` or `fail` |
| `manual` | never | `not_automated` — not a failure |
| `hybrid` | if a policy is configured | automated `fail` is a failure; automated `pass` becomes `needs_evidence` |

Manual and hybrid controls are recorded as observations. They do not create
POA&M items unless the automated half of a hybrid check failed.

Unreviewed **draft** stubs (see [docs/prds/draft-checks.md](prds/draft-checks.md))
are also observations: OSCAL props `result=draft` and `status=draft`, no finding,
no POA&M item. Promote with `enact checks review <id> --reviewer NAME`.

## OSCAL props

On a catalog control, or as Enact extensions on a Component Definition
Validation rule set, these props (namespace `https://grcengineering.club/ns/enact`)
are enough to derive checks.json:

| Prop | Maps to |
| --- | --- |
| `rule-id` (or C2P `Rule_Id` / `Check_Id`) | `rule_id` |
| `check-type` | `check_type` |
| `engine` | `engine` |
| `policy-path` | `policy` |
| `ksi-id` | `ksi_id` |
| `evidence-needed` | `evidence_needed` |

```
enact derive-checks --oscal catalog.json -O checks.json
enact derive-checks --oscal component-definition.json -O checks.json
```
