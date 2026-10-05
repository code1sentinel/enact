# terraform-plan

Input: JSON from `terraform show -json` or a saved plan JSON (`format_version` plus `planned_values`, `values`, or `resource_changes`).

Collector: `enact-adapt-terraform` (`kind=adapter`). Payload: `enact.iam.account-policy` 1.0 only.

This Enact build does **not** ship `enact.logging.audit` or `enact.crypto.posture`. Logging and crypto resources are listed under `skipped` in the mapping report. They are never mapped into invented payload types.

## Mapped

Walks `planned_values.root_module` (and `child_modules`), then state `values.root_module`, then `resource_changes[].change.after`.

| Resource / attribute | Payload field |
| --- | --- |
| `aws_iam_account_password_policy.minimum_password_length` (also `min_password_length`, `minimum_length`) | `password_min_length` |
| `lockout_threshold`, `max_login_attempts`, `failed_attempts` on an IAM-like resource | `lockout_threshold` |
| `mfa_required`, `require_mfa` | `mfa_required` |
| `aws_organizations_policy.content` when it is a parseable SCP | same rules as [aws-scp.md](aws-scp.md) |

## Ignored

Password-policy attributes that have no `enact.iam.account-policy` field: `require_symbols`, `require_numbers`, `require_uppercase_characters`, `require_lowercase_characters`, `allow_users_to_change_password`, `hard_expiry`, `max_password_age`, `password_reuse_prevention`.

## Skipped domains

| Resource types | Report |
| --- | --- |
| `aws_cloudtrail`, `aws_cloudwatch_log_group`, `aws_flow_log`, … | `logging (enact.logging.audit schema not shipped)` |
| `aws_s3_bucket_server_side_encryption_configuration`, `aws_kms_key`, `aws_ebs_encryption_by_default`, … | `crypto (enact.crypto.posture schema not shipped)` |
| Other resource types | skipped by address; not treated as IAM evidence |

## Fail closed

Not terraform JSON, or a plan whose only relevant resources are logging/crypto (no IAM fields): exit 1, no empty envelope.
