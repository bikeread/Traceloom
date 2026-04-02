# QA Playbook

[English](../../en/playbooks/qa.md) | 简体中文

这份 playbook 把 Traceloom MCP contract 包装成面向 QA 的 release confidence 检查路径。

## Recommended questions

- “这个 release 现在能不能发？”
- “哪些 feature artifacts 还存在缺口？”
- “如果这个设计或任务改了，我应该重测哪些东西？”

## MCP tool mapping

- `check_release_readiness(release_target=...)`
- `check_feature_readiness(feature_key=...)`
- `analyze_change_impact(object_id=...)`
- `get_coverage(upstream_type=..., downstream_type=..., relation_type=...)`

## How to interpret outputs

- `release_artifact_ids` 标出当前评审的 release artifact
- `artifact_gap_map` 说明哪一类 artifact 还缺证据
- 下游 impact 帮助判断哪些 task、release 或 review artifact 需要重测

## Drill down further when

- release summary 不是 ready
- coverage 暴露 acceptance 或 review 链路缺失
- impact analysis 触达 test 或 release 层，需要确认重测范围
