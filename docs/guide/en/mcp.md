# MCP Guide

English | [简体中文](../zh-CN/mcp.md)

Traceloom exposes a read-only MCP runtime over the validator, query, workflow, navigation, and design-check layers.
Cherry Studio remains the first official recommended client for the companion demo path, but the same server command also works for other MCP-capable tools.
For the guided demo-first path, see [Cherry Studio Guide](cherry-studio.md).

## Current shape

- read-only MCP surface
- artifact, trace-unit, relation, version, and history lookup
- `get_delivery_slice_navigation`
- `get_artifact_workflow`
- `check_feature_readiness`
- `check_release_readiness`
- `check_design_completeness`
- `analyze_change_impact`

## Start the server

Example repo:

```bash
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
traceloom mcp --paths examples/user-tag-bulk-import
```

Companion demo:

```bash
traceloom mcp --demo --print-tools
traceloom mcp --demo
```

Fallback:

```bash
python -m traceloom mcp --paths examples/user-tag-bulk-import
```

## First closed-loop question flow

Use the runtime to support the first closed loop:

- "Where is this slice now?" -> `get_delivery_slice_navigation`
- "What gate is still blocking this artifact?" -> `get_artifact_workflow`
- "Is the feature ready to move forward?" -> `check_feature_readiness`
- "Is the design complete enough for handoff?" -> `check_design_completeness`
- "What does this change affect?" -> `analyze_change_impact`

The local CLI counterpart for `check_design_completeness` is `design-check`.
The local CLI counterpart for `get_delivery_slice_navigation` is `navigate-feature`.

## Read-only boundary

The public MCP contract stays read-only.
Confirmed local mutation still happens outside MCP through local governed write commands or guided action packages.

That means:

- use MCP to inspect current state
- use `design-check` and `navigate-feature` to drive decisions
- use local CLI commands when you intentionally want to mutate artifact files

## Integration intent

The MCP transport is not the main asset by itself.
The value is the structured artifact runtime that the server exposes:

- typed artifact graph
- workflow and readiness judgments
- stage-aware navigation
- design completeness checks
- consistent JSON payloads for AI clients

For roadmap-facing guidance around this surface, see [Roadmap Guide](roadmap.md).
