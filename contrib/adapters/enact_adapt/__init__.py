"""First-party dump → evidence envelope adapters. Lives outside src/enact."""

from __future__ import annotations

__version__ = "1.0"

COLLECTOR_VERSION = "1.0"
PAYLOAD_TYPE_IAM = "enact.iam.account-policy"
PAYLOAD_VERSION_IAM = "1.0"

IAM_PAYLOAD_FIELDS = (
    "lockout_threshold",
    "account_review_days",
    "privileged_review_days",
    "inactive_disable_days",
    "mfa_required",
    "password_min_length",
)
