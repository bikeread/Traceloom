# PM Playbook

[English](../../en/playbooks/pm.md) | 简体中文

这份 playbook 把 Traceloom MCP contract 包装成面向 PM 的评估路径。
它不会引入新工具，只复用 canonical MCP surface。

## Recommended questions

- “这个 feature 现在能不能继续推进？”
- “现在到底卡在哪一层 artifact？”
- “这次变更下游会影响到谁？”

## MCP tool mapping

- `check_feature_readiness(feature_key=...)`
- `check_release_readiness(release_target=...)`
- `analyze_change_impact(object_id=...)`

## How to interpret outputs

- `ready = false` 表示 feature 或 release 仍有 blocker
- `artifact_gap_map` 说明哪一类 artifact 需要优先处理
- `downstream_artifact_ids` 帮助判断变更会先波及哪些下游文档

## Drill down further when

- `artifact_gap_map` 里出现 blocking gaps，且你需要定位具体文档
- `blocker_count` 非零，且你需要看 validation 明细
- change impact 已经触达 release artifact，需要额外协调交付节奏
