# Cherry Studio Guide

[English](../en/cherry-studio.md) | 简体中文

Cherry Studio 是当前 Traceloom public beta 第一官方推荐客户端。
这份指南只聚焦在 `Path 1: Evaluate Traceloom`。

## Path 1: Evaluate Traceloom

如果你想要最快、最省 setup 的首次体验，就先走这条路径。

- 先在本地安装 Cherry Studio
- 准备好 Traceloom companion executable
- 把 Cherry Studio 连到这个 companion executable
- 启动 `mcp --demo`
- 保持 read-only，会话目标只是评估 bundled demo

companion executable 路径下，Cherry Studio 配置可以直接写成：

```text
command: /path/to/traceloom
arguments: mcp --demo
```

这是当前支持的首条“不需要 Python”的首次体验。
如果团队已经把 companion build 发给你，直接用那一份即可。
如果你手里还没有 companion build，就去打开最新一次成功的 `Build Companion Executable` workflow run，下载对应平台的 artifact，然后使用下载包里的 `traceloom` 可执行文件。
在正式 release artifacts 出来之前，这条 workflow-run 下载路径就是当前的 evaluator fallback。
如果这条路径也暂时不可用，再去看 [Getting Started](getting-started.md) 里的 source-checkout fallback。

## Ask the three readiness questions

让 Cherry Studio 通过 Traceloom MCP server 调用这三类 canonical question flows：

- feature triage: “这个 feature 现在能不能继续推进？”
- release triage: “这个 release 现在能不能发？”
- impact analysis: “这次变更会影响什么？”

预期结果：

- 得到一个可解释的 readiness judgment
- 看见可以继续推进的 blockers 和缺失证据
- 拿到仍然扎根于 repository artifacts 的 impact context

## Path 2: Start a Real Requirement

这份指南到 evaluation path 为止就停下。
如果 demo 已经证明有用，下一步就切到 `Path 2: Start a Real Requirement`。

这条 handoff 仍然应该保持 PM-facing：

- 从当前的 current requirement 出发
- 只在能帮助收窄切片时补充 supporting inputs
- 生成 first baseline
- 回看 open questions 和 next recommended step

入口选择继续看 [Getting Started](getting-started.md)，如果你需要 read-only contract 细节，再看 [MCP Guide](mcp.md)。

## After the first run

- [Getting Started](getting-started.md)：更完整的两路径入口
- [MCP Guide](mcp.md)：公开 read-only contract 细节
