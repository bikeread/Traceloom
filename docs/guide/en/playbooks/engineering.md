# Engineering Playbook

English | [简体中文](../../zh-CN/playbooks/engineering.md)

This playbook packages the Traceloom MCP contract for engineering and tech-lead evaluation.

## Recommended questions

- "Which upstream requirements or constraints feed this design decision?"
- "What downstream tasks and release artifacts will this change affect?"
- "Which artifact version is the active baseline?"

## MCP tool mapping

- `analyze_change_impact(object_id=...)`
- `trace_upstream(trace_unit_id=...)`
- `trace_downstream(trace_unit_id=...)`
- `list_artifact_versions(artifact_id=...)`
- `diff_versions(artifact_id=..., from_version=..., to_version=...)`

## How to interpret outputs

- direct downstream IDs show the immediate implementation surface
- upstream trace-unit IDs show requirements and goals that constrain the change
- version and diff tools explain baseline lineage without polluting readiness summaries

## Drill down further when

- impact analysis reaches a release artifact
- a version family has more than one candidate baseline
- you need exact trace-unit or relation-edge detail for implementation planning
