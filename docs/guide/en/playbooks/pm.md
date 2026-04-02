# PM Playbook

English | [简体中文](../../zh-CN/playbooks/pm.md)

This playbook packages the Traceloom MCP contract for PM-facing evaluation.
It does not introduce new tools; it reuses the canonical MCP surface.

## Recommended questions

- "Is this feature ready to move forward?"
- "Which artifact layer is blocked right now?"
- "What does this change affect downstream?"

## MCP tool mapping

- `check_feature_readiness(feature_key=...)`
- `check_release_readiness(release_target=...)`
- `analyze_change_impact(object_id=...)`

## How to interpret outputs

- `ready = false` means the feature or release still has blockers
- `artifact_gap_map` shows which artifact family needs attention
- `downstream_artifact_ids` helps estimate who will feel a change next

## Drill down further when

- `artifact_gap_map` shows blocking gaps and you need the exact document
- `blocker_count` is non-zero and you need validation detail
- change impact reaches a release artifact and you need delivery coordination
