package enact.encryption_in_transit

import rego.v1

required := input.oscal_params["sc-encryption-in-transit_prm_1"]

result := {
	"passed": input.crypto.tls_required == true,
	"message": sprintf("tls_required is %v; policy requires it to be %v", [input.crypto.tls_required, required]),
}
