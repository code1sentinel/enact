package enact.encryption_at_rest

import rego.v1

required := input.oscal_params["sc-encryption-at-rest_prm_1"]

result := {
	"passed": input.crypto.encryption_at_rest == true,
	"message": sprintf("encryption_at_rest is %v; policy requires it to be %v", [input.crypto.encryption_at_rest, required]),
}
