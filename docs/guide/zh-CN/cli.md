# CLI Guide

[English](../en/cli.md) | 简体中文

CLI 是首版 closed loop 的主要本地 runtime surface。

## Core runtime

首版主路径最重要的命令是：

- `traceloom validate <paths...>`
- `traceloom workflow <artifact_id> --paths ...`
- `traceloom navigate-feature <feature_key> --paths ...`
- `traceloom design-check <feature_key> --paths ...`
- `traceloom mcp --paths ...`

Example:

```bash
traceloom validate examples/user-tag-bulk-import
traceloom workflow PRD-2026-001 --paths examples/user-tag-bulk-import
traceloom navigate-feature user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

这两条闭环读面在 MCP 里的对应关系是：

- `get_delivery_slice_navigation` <-> `navigate-feature`
- `check_design_completeness` <-> `design-check`

公开 MCP contract 继续保持 read-only。

## Query helpers

如果你需要更细的 slice inspection，可以继续用：

- `artifact <artifact_id> --paths ...`
- `unit <trace_unit_id> --paths ...`
- `related <object_id> --paths ...`
- `trace-upstream <trace_unit_id> --paths ...`
- `trace-downstream <trace_unit_id> --paths ...`
- `history <artifact_id> --paths ...`
- `questions --paths ...`
- `versions <artifact_id> --paths ...`
- `diff-versions <artifact_id> <from_version> <to_version> --paths ...`
- `coverage <upstream_type> <downstream_type> --paths ...`

## Local governed write commands

下面这些命令会直接修改本地 artifact 文件：

- `create-artifact-draft`
- `revise-artifact-draft`
- `record-review-decision`
- `record-validation-result`
- `promote-artifact-status`
- `supersede-artifact-version`

它们属于 local governed writes，不属于 public MCP writes。

## Advanced local workflows

这些流程建立在 core runtime 之上：

- `workspace create <name> --root ... [--template minimal|full]`
- `workspace list --root ...`
- `workspace show <name> --root ...`
- `bootstrap prepare --request-file ...`
- `bootstrap apply --seed-file ... --workspace <name> --root ...`
- `prepare-guided-action <feature_key> --paths ... --request-file ...`
- `execute-guided-action --paths ... --package-file ...`

Example:

```bash
traceloom workspace create billing-intake --root ./tmp-workspaces
traceloom bootstrap prepare --request-file ./bootstrap-request.json > ./bootstrap-seed.json
traceloom bootstrap apply --seed-file ./bootstrap-seed.json --workspace billing-intake --root ./tmp-workspaces
```

默认 workspace template 是 `templates/minimal-requirement-repo`。
如果你明确想直接拿到完整六制品骨架，再用 `--template full`。

## Installed entrypoint first

优先使用安装后的 `traceloom` console script：

```bash
traceloom mcp --paths examples/user-tag-bulk-import
```

只有在你把 Traceloom 保留在虚拟环境里时，才使用 module fallback：

```bash
python -m traceloom mcp --paths examples/user-tag-bulk-import
```
