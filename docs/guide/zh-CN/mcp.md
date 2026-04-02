# MCP Guide

[English](../en/mcp.md) | 简体中文

Traceloom 在 validator、query、workflow、navigation 和 design-check 之上暴露了一层 read-only MCP runtime。
Cherry Studio 仍然是 companion demo 路径上的第一推荐 client，但同一条 server command 也能给其他 MCP-capable 工具使用。
guided demo-first 路径见 [Cherry Studio Guide](cherry-studio.md)。

## Current shape

- read-only MCP surface
- artifact、trace-unit、relation、version 和 history lookup
- `get_delivery_slice_navigation`
- `get_artifact_workflow`
- `check_feature_readiness`
- `check_release_readiness`
- `check_design_completeness`
- `analyze_change_impact`

## Start the server

Example repo：

```bash
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
traceloom mcp --paths examples/user-tag-bulk-import
```

Companion demo：

```bash
traceloom mcp --demo --print-tools
traceloom mcp --demo
```

Fallback：

```bash
python -m traceloom mcp --paths examples/user-tag-bulk-import
```

## First closed-loop question flow

围绕首版 closed loop，可以直接问：

- “这个 slice 现在在哪一站？” -> `get_delivery_slice_navigation`
- “这个 artifact 还被什么 gate 卡住？” -> `get_artifact_workflow`
- “这个 feature 能继续往前走吗？” -> `check_feature_readiness`
- “这个 design 现在够不够交接？” -> `check_design_completeness`
- “这个变更会影响什么？” -> `analyze_change_impact`

`check_design_completeness` 的本地 CLI 对应命令是 `design-check`。
`get_delivery_slice_navigation` 的本地 CLI 对应命令是 `navigate-feature`。

## Read-only boundary

公开 MCP contract 继续保持 read-only。
真正确认后的本地 mutation 仍然放在 MCP 之外，通过 local governed write commands 或 guided action packages 完成。

也就是说：

- 用 MCP 读取当前状态
- 用 `design-check` 和 `navigate-feature` 做判断
- 真正要改 artifact 文件时，再切回本地 CLI

## Integration intent

MCP transport 本身不是唯一资产。
真正有价值的是这个 server 暴露出来的 artifact runtime：

- typed artifact graph
- workflow 和 readiness judgments
- stage-aware navigation
- design completeness checks
- 对 AI client 稳定一致的 JSON payload

背后的 roadmap 指南见 [Roadmap Guide](roadmap.md)。
