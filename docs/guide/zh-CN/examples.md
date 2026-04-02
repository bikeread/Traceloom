# Example Matrix

[English](../en/examples.md) | 简体中文

Traceloom 在 public beta 阶段自带一组官方示例仓库和 fixtures。
在打开 Cherry Studio、IDE MCP 客户端或终端工作流之前，可以先用这份指南选择合适的示例材料。

## 官方示例

### Golden-path 示例仓库

路径：`examples/user-tag-bulk-import`

适合用于：

- 干净的首次演示
- 稳定的 feature triage 流程
- 稳定的 release triage 流程
- 稳定的 impact analysis 流程

### Versioned 示例仓库

路径：`examples/user-tag-bulk-import-versioned`

适合用于：

- 跨版本 artifact lineage
- baseline-focused readiness 行为
- version-aware query 和 diff 示例

### Invalid fixture 集合

路径：`examples/invalid`

适合用于：

- 具体验证失败案例
- 损坏的 status transition 或 relation edge
- negative-path 回归夹具

## 什么时候用哪个示例

- public-beta 首次体验先从 `examples/user-tag-bulk-import` 开始
- 需要看版本 lineage 和 baseline 行为时，切到 `examples/user-tag-bulk-import-versioned`
- 需要验证 validator、fixture 或 MCP 错误处理时，使用 `examples/invalid`

## 官方 playbooks

这些 playbooks 不会定义新的 canonical tools。
它们只是把同一套 MCP contract 包装成常见角色的评估路径：

- [PM Playbook](playbooks/pm.md)
- [Engineering Playbook](playbooks/engineering.md)
- [QA Playbook](playbooks/qa.md)
- [Reviewer Playbook](playbooks/reviewer.md)

## Related guides

- [Getting Started](getting-started.md)
- [Cherry Studio Guide](cherry-studio.md)
- [MCP Guide](mcp.md)
