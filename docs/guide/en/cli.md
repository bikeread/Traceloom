# CLI Guide

English | [简体中文](../zh-CN/cli.md)

The CLI is the main local runtime surface for the first closed loop.

## Core runtime

Use these commands for the first public loop:

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

The MCP counterparts for these two closed-loop read surfaces are:

- `get_delivery_slice_navigation` <-> `navigate-feature`
- `check_design_completeness` <-> `design-check`

The public MCP contract remains read-only.

## Query helpers

Use these when you need deeper inspection over the current slice:

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

These commands mutate local artifact files directly:

- `create-artifact-draft`
- `revise-artifact-draft`
- `record-review-decision`
- `record-validation-result`
- `promote-artifact-status`
- `supersede-artifact-version`

They are local governed writes, not public MCP writes.

## Advanced local workflows

These flows sit on top of the core runtime:

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

The default workspace template is `templates/minimal-requirement-repo`.
Use `--template full` when you explicitly want the full six-artifact starter.

## Installed entrypoint first

Prefer the installed `traceloom` console script:

```bash
traceloom mcp --paths examples/user-tag-bulk-import
```

Only use the module fallback when you kept Traceloom inside a virtual environment shell:

```bash
python -m traceloom mcp --paths examples/user-tag-bulk-import
```
