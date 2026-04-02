# Example Matrix

English | [简体中文](../zh-CN/examples.md)

Traceloom ships a small set of official repositories and fixtures for public-beta evaluation.
Use this guide to choose the right example before opening Cherry Studio, an IDE MCP client, or a terminal workflow.

## Official examples

### Golden-path example repository

Path: `examples/user-tag-bulk-import`

Use it when you want:

- the clean first-run demo
- a stable feature triage flow
- a stable release triage flow
- a stable impact analysis flow

### Versioned example repository

Path: `examples/user-tag-bulk-import-versioned`

Use it when you want:

- artifact lineage across versions
- baseline-focused readiness behavior
- version-aware query and diff examples

### Invalid fixture set

Path: `examples/invalid`

Use it when you want:

- concrete validation failure cases
- broken status transitions or relation edges
- regression fixtures for negative-path checks

## When each example is useful

- start with `examples/user-tag-bulk-import` for the public-beta first run
- move to `examples/user-tag-bulk-import-versioned` when you need version lineage and baseline behavior
- use `examples/invalid` when you need to verify validator, fixture, or MCP error handling

## Official playbooks

These playbooks do not define new canonical tools.
They package the same MCP contract for common role-oriented evaluation flows:

- [PM Playbook](playbooks/pm.md)
- [Engineering Playbook](playbooks/engineering.md)
- [QA Playbook](playbooks/qa.md)
- [Reviewer Playbook](playbooks/reviewer.md)

## Related guides

- [Getting Started](getting-started.md)
- [Cherry Studio Guide](cherry-studio.md)
- [MCP Guide](mcp.md)
