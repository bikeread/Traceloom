# Reviewer Playbook

[English](../../en/playbooks/reviewer.md) | 简体中文

这份 playbook 把 Traceloom MCP contract 包装成面向 reviewer 和 release owner 的评估路径。

## Recommended questions

- “这个 release 现在可以批准了吗？”
- “当前 blockers 里哪些是 governance 或 validation 问题，而不只是 open question？”
- “正式 sign off 前，这两个版本到底改了什么？”

## MCP tool mapping

- `check_release_readiness(release_target=...)`
- `get_status_history(artifact_id=...)`
- `list_artifact_versions(artifact_id=...)`
- `diff_versions(artifact_id=..., from_version=..., to_version=...)`
- `validate_repository()`

## How to interpret outputs

- `blockers` 会把 open questions 和 validation failures 分开
- `status_history` 用来查看 promotion 证据
- version 和 diff 输出用来解释批准前到底改了什么

## Drill down further when

- release 还没 ready，但 blocker 来源不清楚
- version lineage 和你的评审预期不一致
- validation failures 需要先在文档层修复后才能批准
