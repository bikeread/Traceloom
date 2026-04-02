# Traceloom

[English](README.md) | 简体中文

Traceloom 是一个 Git-native artifact runtime，用来做可追踪交付治理。
它帮助团队把一条 current requirement 渐进收敛成受治理的 `Brief -> PRD -> Solution Design` slice，通过 read-only MCP 和 CLI 查看当前状态，并在 `design-check` 这一站停下，完成首版闭环。

## 面向谁

- 需要把 artifact governance 接进 Git / CI 的工具与平台工程师
- 需要通过 MCP 获取结构化仓库状态的 AI / agent 集成人员
- 需要判断 readiness、workflow 和 design coverage 的 Tech Lead
- 需要做 evidence-aware handoff review 的 QA / reviewer

## 第一条闭环

当前公开主路径是：

1. 输入一条 current requirement
2. 判断输入是否足够
3. 生成 governed `Brief`
4. 把 slice 长成 `PRD`
5. 创建 `Solution Design`
6. 运行 `design-check`

这条路径故意比完整六制品生命周期更窄。
Execution、Test、Release 仍然保留在 schema 和 runtime 中，但不是首版主产品路径。

## Quickstart

从源码安装：

```bash
git clone https://github.com/bikeread/Traceloom.git
cd Traceloom
pipx install ./
pipx ensurepath
```

跑通 example：

```bash
traceloom validate examples/user-tag-bulk-import
traceloom navigate-feature user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

一次性的 `uv` fallback：

```bash
uvx --from . traceloom validate examples/user-tag-bulk-import
uvx --from . traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
```

## 真实项目如何开始

在真实项目里，从 current requirement 开始，而不是一上来面对六份文档。

- 创建一个 minimal workspace
- 对 current requirement 运行 bootstrap prepare
- materialize 第一份 baseline
- 迭代直到 slice 能长成 `PRD`
- 创建 `Solution Design`
- 运行 `design-check`

首选起点是 `templates/minimal-requirement-repo`。
只有当你明确想直接拿到完整六制品骨架时，才使用 `templates/starter-repo`。

## Core runtime

核心 runtime 命令包括：

- `validate`
- `artifact`, `unit`, `related`, `trace-upstream`, `trace-downstream`
- `history`, `questions`, `versions`, `diff-versions`, `coverage`
- `workflow`
- `navigate-feature`
- `design-check`
- `mcp`

这些命令暴露的是 protocol core、query layer、workflow model 和 read-only MCP runtime，而不是一个新的工作台。

## Local governed writes

Traceloom 也提供窄写入命令：

- `create-artifact-draft`
- `revise-artifact-draft`
- `record-review-decision`
- `record-validation-result`
- `promote-artifact-status`
- `supersede-artifact-version`

这些命令只更新本地 artifact 文件。
公开 MCP contract 继续保持 read-only。

## Advanced workflows

下面这些能力保留，但不再作为首版 OSS front door：

- `workspace create/list/show`
- `bootstrap prepare/apply`
- `prepare-guided-action`
- `execute-guided-action`

把它们理解为构建在 core runtime 之上的 advanced local workflows。

## Advanced setup

`companion executable` 仍然可用，适合 guided demo-first 体验。
Cherry Studio 可以这样启动：

```text
command: /path/to/traceloom
arguments: mcp --demo
```

companion smoke：

```bash
traceloom mcp --demo --print-tools
```

## Public docs

- [Getting Started](docs/guide/zh-CN/getting-started.md)
- [Cherry Studio Guide](docs/guide/zh-CN/cherry-studio.md)
- [CLI Guide](docs/guide/zh-CN/cli.md)
- [Example Matrix And Playbooks](docs/guide/zh-CN/examples.md)
- [MCP Guide](docs/guide/zh-CN/mcp.md)
- [Schema Guide](docs/guide/zh-CN/schema.md)
- [Roadmap Guide](docs/guide/zh-CN/roadmap.md)

## Repository layout

- `traceloom/`: protocol runtime、validator、query layer、workflow/navigation、MCP wrapper 和 CLI
- `tests/`: parsing、validation、CLI、MCP、workspace/bootstrap 和 docs surface 的回归测试
- `examples/`: golden path、versioned 和 invalid artifact 仓库
- `templates/minimal-requirement-repo/`: minimal `Brief` 起步模板
- `templates/starter-repo/`: 完整六制品 starter template
- `docs/guide/`: 公开使用文档

## Implementation source of truth

- 结构化实现规则位于 [04_schema_v1.yaml](04_schema_v1.yaml)
- 如果叙述性说明和 runtime 规则冲突，以 [04_schema_v1.yaml](04_schema_v1.yaml) 为准
- 打包 runtime 使用的副本位于 [traceloom/resources/04_schema_v1.yaml](traceloom/resources/04_schema_v1.yaml)
