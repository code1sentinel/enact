# aws-scp

Input: an Organizations SCP or IAM policy document:

- a raw policy (`Version` + `Statement`)
- `aws organizations describe-policy` JSON (`Policy.Content`, string or object)
- `PolicyDocument` / `Policies[]` wrappers

Collector: `enact-adapt-aws-scp` (`kind=adapter`). Payload: `enact.iam.account-policy` 1.0.

Only **explicit** numeric or MFA conditions are mapped. A Deny of `iam:UpdateAccountPasswordPolicy` with no condition is **not** treated as a password length. The adapter never invents pass fields from Sid names or action lists.

## Mapped

| Condition | Payload field |
| --- | --- |
| Deny `NumericLessThan` on `iam:MinimumPasswordLength` / `iam:PasswordMinLength` (value N) | `password_min_length` = N |
| Allow/Deny `NumericGreaterThanEquals` or `NumericEquals` on those keys | `password_min_length` |
| Deny `BoolIfExists`/`Bool` `aws:MultiFactorAuthPresent` = false | `mfa_required` = true |
| Deny `NumericGreaterThan` on `iam:LockoutThreshold` (value N) | `lockout_threshold` = N |

Absence of an MFA statement is not mapped as `mfa_required: false`.

## Skipped (typical)

- Deny `s3:*` / other non-IAM services
- Deny `iam:DeleteAccountPasswordPolicy` or `iam:UpdateAccountPasswordPolicy` with **no** numeric/MFA condition
- Condition keys that are not a clear account-policy constraint

Each skipped statement is listed by `Sid` (or index) in the mapping report.

## Fail closed

Unparseable JSON or Content string, a terraform dump passed to this adapter, or a policy whose statements are all unmappable: exit 1, no output file.
