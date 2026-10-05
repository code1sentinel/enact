package enact.account_review

import rego.v1

# Threshold comes from the OSCAL parameter, not from this file.
threshold := to_number(input.oscal_params["c-ac-2_prm_1"])

configured := input.payload.account_review_days

default passed := false

passed if {
	is_number(configured)
	configured > 0
	configured <= threshold
}

result := {
	"passed": passed,
	"message": sprintf("account_review_days is %v; policy allows at most %v days", [configured, threshold]),
}
