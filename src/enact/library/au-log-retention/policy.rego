package enact.log_retention

import rego.v1

threshold := to_number(input.oscal_params["au-log-retention_prm_1"])

configured := input.logging.retention_days

default passed := false

passed if {
	is_number(configured)
	configured >= threshold
}

result := {
	"passed": passed,
	"message": sprintf("retention_days is %v; policy requires at least %v days", [configured, threshold]),
}
