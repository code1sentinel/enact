# Check manifest convention

Enact maps OSCAL controls to runnable checks with a small JSON document, or
with the same fields stored as OSCAL props.

Parameters are **not** duplicated here. The manifest names the OSCAL param
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
| `evidence` | no | Path to supporting evidence linked from the report. |
| `evidence_needed` | manual/hybrid | What a person must still provide. |
| `review_status` | draft checks | `draft` until `enact checks review`. Draft results never count as passed. |

The JSON Schema is [`schemas/check-manifest.schema.json`](../schemas/check-manifest.schema.json).

## Rule ID

Use a lowercase, hyphenated id that names the *check*, not the engine:

- `ac-login-lockout`
- `ac-account-review`

Do not encode the control catalog version in the rule id. The control id
already does that. The same rule can satisfy more than one control by
repeating the row with a different `control_id`.

C2P-style `Rule_Id` / `Check_Id` props are accepted as aliases when the
manifest is derived from OSCAL.

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

On a catalog control or a component-definition `implemented-requirement`,
these props (namespace `https://grcengineering.club/ns/enact`) are enough
to derive a manifest:

| Prop | Maps to |
| --- | --- |
| `rule-id` (or C2P `Rule_Id` / `Check_Id`) | `rule_id` |
| `check-type` | `check_type` |
| `engine` | `engine` |
| `policy-path` | `policy` |
| `ksi-id` | `ksi_id` |
| `evidence-needed` | `evidence_needed` |

```
enact derive-manifest --oscal catalog.json -O manifest.json
```
