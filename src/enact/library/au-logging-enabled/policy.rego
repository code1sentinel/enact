package enact.logging_enabled

import rego.v1

required := input.oscal_params["au-logging-enabled_prm_1"]

result := {
	"passed": input.logging.audit_enabled == true,
	"message": sprintf("audit_enabled is %v; policy requires logging to be %v", [input.logging.audit_enabled, required]),
}
