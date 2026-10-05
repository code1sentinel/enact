# aws-iam-password-policy

Input: JSON from `aws iam get-account-password-policy`, or an equivalent fixture that wraps `PasswordPolicy` and optional account-summary / lockout fields.

Collector: `enact-adapt-aws-iam` (`kind=adapter`). Payload: `enact.iam.account-policy` 1.0.

## Mapped

| Source key | Payload field |
| --- | --- |
| `MinimumPasswordLength` (also `minimum_password_length`, `MinPasswordLength`, `MinimumLength`) | `password_min_length` |
| `LockoutThreshold` (also `lockout_threshold`, `MaxPasswordAttempts`, `MaxLoginAttempts`, `FailedLoginAttempts`) | `lockout_threshold` |
| `AccountMFAEnabled` (0/1 or bool), `RequireMFA`, `MFARequired`, `mfa_required` | `mfa_required` |

`AccountMFAEnabled` is accepted from a sibling `SummaryMap` (the shape of `aws iam get-account-summary`) when the dump is a combined export. Official password-policy JSON does not include lockout or MFA; those keys are mapped **only when present**. Empty fields are omitted from the payload, not filled with invented defaults.

## Ignored (typical password-policy keys)

`AllowUsersToChangePassword`, `ExpirePasswords`, `HardExpiry`, `MaxPasswordAge`, `PasswordReusePrevention`, `RequireLowercaseCharacters`, `RequireNumbers`, `RequireSymbols`, `RequireUppercaseCharacters`, plus unrelated summary counters such as `Users` / `UsersQuota`.

## Empty (schema fields this dump usually cannot fill)

`account_review_days`, `privileged_review_days`, `inactive_disable_days`, and lockout/MFA when those keys are absent.

## Fail closed

Unparseable JSON, a dump that looks like Terraform, or an object with no password-policy / MFA / lockout keys: exit 1, no output file. A recognized dump that maps zero fields also refuses to write an empty envelope.
