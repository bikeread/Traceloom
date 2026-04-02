# Getting Started

[English](../en/getting-started.md) | 简体中文

Traceloom 是一个 Git-native artifact runtime。
首版公开主路径是一条很窄的 closed loop：从一条 current requirement 出发，渐进长成 `Brief`、`PRD`、`Solution Design`，最后通过 `design-check`。

## First Closed Loop

当你想把一条 current requirement 收成 governed baseline 时，就走这条路径：

1. 输入 current requirement
2. 运行 bootstrap preparation
3. materialize 一份 `Brief`
4. 把 slice 长成 `PRD`
5. 创建 `Solution Design`
6. 用 `design-check` 再检查一次

这是当前 OSS runtime 的默认产品路径。

## Quickstart

从源码安装：

```bash
git clone https://github.com/bikeread/Traceloom.git
cd Traceloom
pipx install ./
pipx ensurepath
```

先跑 bundled example：

```bash
traceloom validate examples/user-tag-bulk-import
traceloom navigate-feature user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

## 真实项目路径

在真实项目里：

1. 创建 minimal workspace
2. 从 current requirement 准备 bootstrap request
3. apply 第一份 baseline
4. 迭代直到 `PRD` 足够稳定，可以 handoff 给设计
5. 创建 `Solution Design`
6. 用 `design-check` 重新判断完备性

这条路径的默认起点是 `templates/minimal-requirement-repo`。
只有当你明确想马上拿到完整六制品骨架时，才使用 `templates/starter-repo`。

## Core runtime

当前最重要的 runtime surface 是：

- `validate`
- `workflow`
- `navigate-feature`
- `design-check`
- `mcp`

完整命令面见 [CLI Guide](cli.md)。
如果你想把相同仓库状态暴露给 AI client，见 [MCP Guide](mcp.md)。

## Advanced workflows

下面这些能力继续保留，但不再是主入口：

- workspace 管理
- bootstrap apply 细节
- guided action package
- local companion execution

这些 advanced local workflows 都放在 [CLI Guide](cli.md) 里。

## Advanced setup

`companion executable` 仍可用于 guided demo-first 体验。
Cherry Studio 启动方式：

```text
command: /path/to/traceloom
arguments: mcp --demo
```

companion smoke：

```bash
traceloom mcp --demo --print-tools
```

## Next guides

- [Cherry Studio Guide](cherry-studio.md)
- [CLI Guide](cli.md)
- [MCP Guide](mcp.md)
- [Example Matrix](examples.md)
- [Schema Guide](schema.md)
- [Roadmap Guide](roadmap.md)
