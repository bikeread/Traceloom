# Engineering Playbook

[English](../../en/playbooks/engineering.md) | 简体中文

这份 playbook 把 Traceloom MCP contract 包装成面向工程和 tech lead 的评估路径。

## Recommended questions

- “这个设计决策上游依赖哪些需求或约束？”
- “这次变更下游会影响哪些任务和 release artifact？”
- “当前哪个版本才是 active baseline？”

## MCP tool mapping

- `analyze_change_impact(object_id=...)`
- `trace_upstream(trace_unit_id=...)`
- `trace_downstream(trace_unit_id=...)`
- `list_artifact_versions(artifact_id=...)`
- `diff_versions(artifact_id=..., from_version=..., to_version=...)`

## How to interpret outputs

- 直接下游 IDs 表示最先受影响的实现面
- 上游 trace-unit IDs 表示约束这次变更的需求和目标
- version 和 diff 工具用于解释 baseline lineage，而不是把这些细节混进 readiness summary

## Drill down further when

- impact analysis 已经触达 release artifact
- 一个 version family 看起来不止一个 baseline 候选
- 你需要更细的 trace-unit 或 relation-edge 细节来做实现规划
