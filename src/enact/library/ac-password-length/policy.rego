package enact.password_length

import rego.v1

threshold := to_number(input.oscal_params["ac-password-length_prm_1"])

configured := input.iam.password_min_length

default passed := false

passed if {
	is_number(configured)
	configured >= threshold
}

result := {
	"passed": passed,
	"message": sprintf("password_min_length is %v; policy requires at least %v characters", [configured, threshold]),
}
