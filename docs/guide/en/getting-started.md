# Getting Started

English | [简体中文](../zh-CN/getting-started.md)

Traceloom is a Git-native artifact runtime.
The first public product path is a narrow closed loop that starts from one current requirement and grows it through `Brief`, `PRD`, `Solution Design`, and `design-check`.

## First Closed Loop

Use this path when you want to move one current requirement into a governed baseline:

1. capture the current requirement
2. run bootstrap preparation
3. materialize a `Brief`
4. grow the slice into `PRD`
5. create `Solution Design`
6. run `design-check`

This is the default product story for the open-source runtime.

## Quickstart

Install from source:

```bash
git clone https://github.com/bikeread/Traceloom.git
cd Traceloom
pipx install ./
pipx ensurepath
```

Validate and inspect the bundled example:

```bash
traceloom validate examples/user-tag-bulk-import
traceloom navigate-feature user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

## Real Project Flow

For a real project:

1. create a minimal workspace
2. prepare a bootstrap request from the current requirement
3. apply the first baseline
4. iterate until `PRD` is stable enough for design kickoff
5. create `Solution Design`
6. re-check completeness with `design-check`

Start from `templates/minimal-requirement-repo` for this loop.
Use `templates/starter-repo` only when you explicitly want the full six-artifact scaffold immediately.

## Core runtime

The main runtime surfaces are:

- `validate`
- `workflow`
- `navigate-feature`
- `design-check`
- `mcp`

Use the [CLI Guide](cli.md) for the full command surface.
Use the [MCP Guide](mcp.md) when you want to expose the same repository state to AI clients.

## Advanced workflows

These flows remain available but are no longer the main front door:

- workspace management
- bootstrap apply details
- guided action packages
- local companion execution

See the [CLI Guide](cli.md) for those advanced local workflows.

## Advanced setup

The companion executable still exists for a guided demo-first experience.
Cherry Studio can launch it with:

```text
command: /path/to/traceloom
arguments: mcp --demo
```

Companion smoke:

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
