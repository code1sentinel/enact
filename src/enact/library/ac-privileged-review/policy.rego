package enact.privileged_review

import rego.v1

threshold := to_number(input.oscal_params["ac-privileged-review_prm_1"])

configured := input.iam.privileged_review_days

default passed := false

passed if {
	is_number(configured)
	configured > 0
	configured <= threshold
}

result := {
	"passed": passed,
	"message": sprintf("privileged_review_days is %v; policy allows at most %v days", [configured, threshold]),
}
