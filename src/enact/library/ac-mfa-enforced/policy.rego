package enact.mfa_enforced

import rego.v1

scope := input.oscal_params["ac-mfa-enforced_prm_1"]

result := {
	"passed": input.iam.mfa_required == true,
	"message": sprintf("mfa_required is %v; policy requires MFA for %v users", [input.iam.mfa_required, scope]),
}
