package enact.inactive_disable

import rego.v1

threshold := to_number(input.oscal_params["ac-inactive-disable_prm_1"])

configured := input.iam.inactive_disable_days

default passed := false

passed if {
	is_number(configured)
	configured > 0
	configured <= threshold
}

result := {
	"passed": passed,
	"message": sprintf("inactive_disable_days is %v; policy allows at most %v idle days", [configured, threshold]),
}
