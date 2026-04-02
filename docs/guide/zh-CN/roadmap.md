# Roadmap Guide

[English](../en/roadmap.md) | 简体中文

runtime MVP 已经完成。
Track A、Track B 和 Track C 的第一批 slice 已经到位。
当前近期工作重点已经转到 companion executable packaging，也就是在 beta hardening 之后把 outsider 路径真正打包成可下载产品，而不是继续扩大 canonical runtime surface。

## Current priority order

1. 持续保持 companion executable packaging 的一致性，包括 bundled demo assets、`mcp --demo` 和 companion build/smoke paths
2. 在薄 workspace substrate 上执行 current-requirement bootstrap 这条下一条产品路径
3. 在公开 MCP surface 继续只读的前提下，把本地 governed companion flow 扩到基于 workspace 的 guided validation
4. 只有当 companion 路径和 bootstrap 路径在反复验证下都保持一致后，才扩大 non-developer distribution
5. 只有当 companion outsider path 在反复验证下保持一致后，才进入 adapters
