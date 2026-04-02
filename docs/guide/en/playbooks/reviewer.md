# Reviewer Playbook

English | [简体中文](../../zh-CN/playbooks/reviewer.md)

This playbook packages the Traceloom MCP contract for reviewers and release owners.

## Recommended questions

- "Is this release ready to approve?"
- "Which blockers are governance or validation issues rather than open questions?"
- "What changed across versions before I sign off?"

## MCP tool mapping

- `check_release_readiness(release_target=...)`
- `get_status_history(artifact_id=...)`
- `list_artifact_versions(artifact_id=...)`
- `diff_versions(artifact_id=..., from_version=..., to_version=...)`
- `validate_repository()`

## How to interpret outputs

- `blockers` separates open questions from validation failures
- `status_history` shows promotion evidence
- version and diff outputs show what changed before approval

## Drill down further when

- a release is not ready but the blocker source is unclear
- version lineage looks inconsistent with review expectations
- validation failures need document-level remediation before approval
