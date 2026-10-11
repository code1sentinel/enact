# Writing custom checks

The hosted Pages app runs the precompiled starter library. There is no in-browser Rego compiler. Custom Rego, `opa test`, and draft **review** stay on the **CLI**. Localhost `enact ui` can generate draft stubs for unmatched catalog controls; those stubs stay draft until `enact checks review`.

{% hint style="info" %}
Install Python 3.10+ and the OPA 1.8.x binary on `PATH`, then `pip install -e ".[dev]"` or `uv sync --extra dev`. `ENACT_OPA` overrides the binary path.
{% endhint %}

## Start from the library

```bash
enact checks list
enact checks show ac-login-lockout
enact init --check ac-login-lockout --check au-logging-enabled --out my-project
```

`enact init` writes a runnable folder: catalog (or a mapping onto your `--oscal` catalog), `checks.json`, Rego, sample input, and a GitHub Actions workflow.

## checks.json row

```json
{
  "schema_version": "1.0",
  "checks": [
    {
      "rule_id": "ac-login-lockout",
      "control_id": "c-ac-7",
      "check_type": "automated",
      "engine": "opa",
      "policy": "policies/login_lockout.rego",
      "params": ["c-ac-7_prm_1"]
    }
  ]
}
```

- **`rule_id`** names the implementation. **`control_id`** is the OSCAL control.
- **`params`** lists OSCAL parameter ids. Values come from the catalog, not from this file.
- **`check_type`**: `automated` | `manual` | `hybrid`.
- Automated checks that declare `payload_type` must see a valid envelope field; missing evidence is `status=error` (message starts with `evidence:`), never `pass`.

The same mapping can be an OSCAL Component Definition. Convert with `enact emit-component-definition`. See [Concepts](concepts.md).

## Rego contract

Policies are Rego v1 and expose `result`:

```rego
package enact.login_lockout

import rego.v1

threshold := to_number(input.oscal_params["c-ac-7_prm_1"])

configured := input.payload.lockout_threshold

default passed := false

passed if {
	is_number(configured)
	configured > 0
	configured <= threshold
}

result := {
	"passed": passed,
	"message": sprintf("lockout_threshold is %v; policy allows at most %v failed attempts", [configured, threshold]),
}
```

The runner queries `data.<package>.result` unless you set `query`. Change the lockout in OSCAL; do not hard-code the number in Rego.

## Draft checks from unmatched controls

A catalog can contain controls the library does not cover. `enact checks draft` writes a deterministic stub — no network, no model.

```bash
enact checks draft --oscal catalog.json --out drafts
enact checks list --status draft --drafts drafts
enact run --oscal catalog.json --checks checks.json --drafts drafts --input evidence.json --workdir . --out out
enact checks review draft-c-cm-2 --reviewer "Your Name" --note "accepted stub" --drafts drafts --library library
```

- Drafts live under `drafts/<id>/` with `status=draft`.
- `rule_id` is `draft-<oscal-control-id>`.
- Unreviewed drafts included with `--drafts` render as **Draft**. They never increment the pass count and never open a POA&M item.
- Generation alone does not promote. `enact checks review` requires a reviewer name.

## opa test

OPA 1.8.x, Rego v1:

```bash
opa test path/to/policies -v
```

A test should use a worked input, not restate the production rule:

```rego
package enact.login_lockout_test

import data.enact.login_lockout

test_passes_when_threshold_at_param if {
	got := login_lockout.result with input as {
		"oscal_params": {"c-ac-7_prm_1": "5"},
		"payload": {"lockout_threshold": 5},
	}
	got.passed == true
}
```

Library checks also ship pass/fail samples next to the policy. Those samples are the independent expected values.

Then run the same files through Enact:

```bash
enact run --oscal catalog.json --checks checks.json --input evidence.json --workdir . --out out
enact validate --assessment-results out/assessment-results.json --poam out/poam.json
```
