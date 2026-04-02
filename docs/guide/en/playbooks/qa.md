# QA Playbook

English | [简体中文](../../zh-CN/playbooks/qa.md)

This playbook packages the Traceloom MCP contract for QA-oriented release confidence checks.

## Recommended questions

- "Is this release ready?"
- "Which feature artifacts still have open gaps?"
- "What should I retest if this design or task changes?"

## MCP tool mapping

- `check_release_readiness(release_target=...)`
- `check_feature_readiness(feature_key=...)`
- `analyze_change_impact(object_id=...)`
- `get_coverage(upstream_type=..., downstream_type=..., relation_type=...)`

## How to interpret outputs

- `release_artifact_ids` identifies the release artifact under review
- `artifact_gap_map` shows which artifact family still lacks evidence
- downstream impact highlights which tasks, release, or review artifacts need retesting

## Drill down further when

- the release summary is not ready
- coverage shows missing acceptance or review linkage
- impact analysis reaches test or release layers and you need scope confirmation
