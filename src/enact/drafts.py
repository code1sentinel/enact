"""Generate, list, and review draft Rego checks for unmatched OSCAL controls."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from enact.library import LibraryCheck, normalize_control_id, oscal_control_id
from enact.models import CheckSpec, Manifest, ReviewStatus
from enact.oscal_io import ControlRecord, OscalBundle

Clock = Callable[[], datetime]
DRAFT_STATUS = "draft"
REVIEWED_STATUS = "reviewed"


class DraftError(ValueError):
    """User-facing draft generate/review error."""


@dataclass
class DraftCheck:
    rule_id: str
    control_id: str
    title: str
    statement: str
    statement_hash: str
    package: str
    status: str
    generated_at: str
    policy: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    review_note: str | None = None
    directory: Path | None = None

    def to_spec(self, *, policy: str) -> CheckSpec:
        review: ReviewStatus | None = "draft" if self.status == DRAFT_STATUS else None
        return CheckSpec(
            rule_id=self.rule_id,
            control_id=self.control_id,
            check_type="automated",
            engine="opa",
            policy=policy,
            title=self.title,
            description=self.statement or self.title,
            review_status=review,
        )

    def to_meta(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "control_id": self.control_id,
            "source_control_id": self.control_id,
            "title": self.title,
            "description": self.statement,
            "statement_hash": self.statement_hash,
            "package": self.package,
            "status": self.status,
            "generated_at": self.generated_at,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "review_note": self.review_note,
            "check_type": "automated",
            "engine": "opa",
        }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def statement_hash(text: str) -> str:
    normalized = " ".join((text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def draft_rule_id(control_id: str) -> str:
    return f"draft-{oscal_control_id(control_id)}"


def draft_package_name(control_id: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "_", oscal_control_id(control_id)).strip("_")
    return f"enact.draft_{token or 'control'}"


def unmatched_controls(
    bundle: OscalBundle,
    library: Iterable[LibraryCheck],
    manifest: Manifest | None = None,
) -> list[ControlRecord]:
    """Controls with no bundled library check and no manifest row."""
    checks = list(library)
    library_ids = {check.rule_id for check in checks}
    suggested = set()
    for check in checks:
        suggested.add(normalize_control_id(check.rule_id))
        suggested.update(normalize_control_id(item) for item in check.suggested_controls)
    mapped = set()
    if manifest:
        for spec in manifest.checks:
            mapped.add(normalize_control_id(spec.control_id))
    missing: list[ControlRecord] = []
    for record in bundle.controls.values():
        if normalize_control_id(record.control_id) in mapped:
            continue
        rule_id = record.props.get("rule-id")
        if rule_id and rule_id in library_ids:
            continue
        if normalize_control_id(record.control_id) in suggested:
            continue
        missing.append(record)
    return missing


def render_draft_policy(record: ControlRecord, *, generated_at: str) -> str:
    rule_id = draft_rule_id(record.control_id)
    package = draft_package_name(record.control_id)
    digest = statement_hash(record.statement)
    title = record.title or record.control_id
    statement = record.statement or title
    comment_lines = [f"#   {line}" if line else "#" for line in statement.splitlines()] or ["#   (no statement)"]
    statement_block = "\n".join(comment_lines)
    return f"""# Enact draft check — unreviewed. Do not treat results as trusted.
# Generated from OSCAL control {record.control_id} at {generated_at}.
# statement_hash: {digest}
#
# Title: {title}
# Statement:
{statement_block}
#
# TODO: confirm the input JSON path this check should read.
# TODO: replace the stub assertion with the real condition.
# TODO: run `enact checks review {rule_id} --reviewer YOUR_NAME` after you accept it.

package {package}

import rego.v1

control_id := "{record.control_id}"

default passed := false

# Unreviewed drafts never pass. A reviewer must replace this rule.
passed if {{
	false
	# TODO: input.some.path == expected_value
}}

result := {{
	"passed": passed,
	"draft": true,
	"message": sprintf("draft check for %s is unreviewed; edit the TODOs then run enact checks review", [control_id]),
}}
"""


def generate_drafts(
    bundle: OscalBundle,
    dest: Path,
    *,
    library: Iterable[LibraryCheck],
    manifest: Manifest | None = None,
    clock: Clock = utcnow,
) -> list[DraftCheck]:
    missing = unmatched_controls(bundle, library, manifest)
    created: list[DraftCheck] = []
    if not missing:
        return created
    dest.mkdir(parents=True, exist_ok=True)
    stamp = iso_utc(clock())
    for record in missing:
        created.append(_write_draft(record, dest, generated_at=stamp))
    return created


def _write_draft(record: ControlRecord, dest: Path, *, generated_at: str) -> DraftCheck:
    rule_id = draft_rule_id(record.control_id)
    folder = dest / rule_id
    folder.mkdir(parents=True, exist_ok=True)
    policy = render_draft_policy(record, generated_at=generated_at)
    draft = DraftCheck(
        rule_id=rule_id,
        control_id=record.control_id,
        title=record.title or record.control_id,
        statement=record.statement,
        statement_hash=statement_hash(record.statement),
        package=draft_package_name(record.control_id),
        status=DRAFT_STATUS,
        generated_at=generated_at,
        policy=policy,
        directory=folder,
    )
    (folder / "policy.rego").write_text(policy if policy.endswith("\n") else policy + "\n", encoding="utf-8")
    (folder / "check.json").write_text(json.dumps(draft.to_meta(), indent=2) + "\n", encoding="utf-8")
    return draft


def load_draft(directory: Path) -> DraftCheck:
    meta_path = directory / "check.json"
    if not meta_path.is_file():
        raise DraftError(f"{directory} has no check.json")
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    policy_path = directory / "policy.rego"
    return DraftCheck(
        rule_id=str(data["rule_id"]),
        control_id=str(data.get("control_id") or data.get("source_control_id") or directory.name),
        title=str(data.get("title") or data["rule_id"]),
        statement=str(data.get("description") or ""),
        statement_hash=str(data.get("statement_hash") or ""),
        package=str(data.get("package") or draft_package_name(str(data.get("control_id") or directory.name))),
        status=str(data.get("status") or DRAFT_STATUS),
        generated_at=str(data.get("generated_at") or ""),
        policy=policy_path.read_text(encoding="utf-8") if policy_path.is_file() else "",
        reviewer=data.get("reviewer"),
        reviewed_at=data.get("reviewed_at"),
        review_note=data.get("review_note"),
        directory=directory,
    )


def list_drafts(directory: Path, *, status: str | None = DRAFT_STATUS) -> list[DraftCheck]:
    if not directory.is_dir():
        return []
    drafts = [load_draft(path) for path in sorted(directory.iterdir()) if path.is_dir() and (path / "check.json").is_file()]
    if status:
        drafts = [item for item in drafts if item.status == status]
    return drafts


def review_draft(
    rule_id: str,
    *,
    drafts_dir: Path,
    library_dir: Path,
    reviewer: str,
    note: str | None = None,
    clock: Clock = utcnow,
) -> DraftCheck:
    if not (reviewer or "").strip():
        raise DraftError("reviewer is required; generation never promotes a draft")
    source = drafts_dir / rule_id
    if not (source / "check.json").is_file():
        raise DraftError(f"unknown draft {rule_id!r}. Generate one with `enact checks draft`.")
    draft = load_draft(source)
    if draft.status != DRAFT_STATUS:
        raise DraftError(f"{rule_id} is {draft.status}, not draft")
    draft.status = REVIEWED_STATUS
    draft.reviewer = reviewer.strip()
    draft.review_note = (note or "").strip() or None
    draft.reviewed_at = iso_utc(clock())
    library_dir.mkdir(parents=True, exist_ok=True)
    dest = library_dir / rule_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(source), str(dest))
    draft.directory = dest
    (dest / "check.json").write_text(json.dumps(draft.to_meta(), indent=2) + "\n", encoding="utf-8")
    return draft


def policy_path_for(draft: DraftCheck, workdir: Path) -> str:
    if not draft.directory:
        raise DraftError(f"{draft.rule_id} has no directory")
    path = (draft.directory / "policy.rego").resolve()
    try:
        return str(path.relative_to(workdir.resolve()))
    except ValueError:
        return str(path)


def attach_drafts(manifest: Manifest, drafts_dir: Path, workdir: Path) -> Manifest:
    """Append unreviewed drafts for controls the manifest does not already cover."""
    covered = {normalize_control_id(spec.control_id) for spec in manifest.checks}
    extras = []
    for draft in list_drafts(drafts_dir, status=DRAFT_STATUS):
        if normalize_control_id(draft.control_id) in covered:
            continue
        extras.append(draft.to_spec(policy=policy_path_for(draft, workdir)))
        covered.add(normalize_control_id(draft.control_id))
    if not extras:
        return manifest
    return Manifest(
        schema_version=manifest.schema_version,
        title=manifest.title,
        checks=[*manifest.checks, *extras],
        source=manifest.source or "drafts",
    )


def drafts_as_dicts(drafts: Iterable[DraftCheck]) -> list[dict[str, object]]:
    return [{**item.to_meta(), "policy": item.policy} for item in drafts]
