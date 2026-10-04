package enact.login_lockout

import rego.v1

threshold := to_number(input.oscal_params["ac-login-lockout_prm_1"])

configured := input.iam.lockout_threshold

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
