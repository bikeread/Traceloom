# Traceloom

English | [简体中文](README.zh-CN.md)

Traceloom is a Git-native artifact runtime for traceable delivery governance.
It helps teams turn one current requirement into a governed `Brief -> PRD -> Solution Design` slice, inspect the slice through read-only MCP and CLI surfaces, and stop cleanly at `design-check` before wider execution planning.

## Who It Is For

- tooling and platform engineers wiring artifact governance into Git and CI
- AI and agent integrators who need structured repository state over MCP
- tech leads who need readiness, workflow, and design-coverage judgment
- QA and reviewers who need evidence-aware handoff visibility

## First Closed Loop

The first public closed loop is:

1. capture one current requirement
2. check whether the input is sufficient
3. generate a governed `Brief`
4. grow the slice into `PRD`
5. create `Solution Design`
6. run `design-check` before handoff

This path is intentionally narrower than the full six-artifact lifecycle.
Execution, test, and release artifacts remain in the schema and runtime, but they are not the first required product path.

## Quickstart

Install from a source checkout:

```bash
git clone https://github.com/bikeread/Traceloom.git
cd Traceloom
pipx install ./
pipx ensurepath
```

Validate the example repository:

```bash
traceloom validate examples/user-tag-bulk-import
traceloom navigate-feature user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

Disposable `uv` fallback:

```bash
uvx --from . traceloom validate examples/user-tag-bulk-import
uvx --from . traceloom design-check user-tag-bulk-import --paths examples/user-tag-bulk-import
```

## Real Project Start

For a real project, start from the current requirement rather than from six pre-filled files.

- create a minimal workspace
- run bootstrap preparation on the current requirement
- materialize the first baseline
- iterate until the slice is ready for `PRD`
- create `Solution Design`
- run `design-check`

Use `templates/minimal-requirement-repo` as the default starting point for this first closed loop.
Use `templates/starter-repo` only when you explicitly want the full six-artifact scaffold up front.

## Core Runtime

The core runtime surface is:

- `validate`
- `artifact`, `unit`, `related`, `trace-upstream`, `trace-downstream`
- `history`, `questions`, `versions`, `diff-versions`, `coverage`
- `workflow`
- `navigate-feature`
- `design-check`
- `mcp`

These commands expose the protocol core, query layer, workflow model, and read-only MCP runtime without requiring a separate workbench.

## Local Governed Writes

Traceloom also includes narrow local write helpers:

- `create-artifact-draft`
- `revise-artifact-draft`
- `record-review-decision`
- `record-validation-result`
- `promote-artifact-status`
- `supersede-artifact-version`

These commands update local artifact files directly.
The public MCP contract remains read-only.

## Advanced Workflows

The following flows remain available but are not the primary OSS front door:

- `workspace create/list/show`
- `bootstrap prepare/apply`
- `prepare-guided-action`
- `execute-guided-action`

Treat these as advanced local workflows that sit on top of the core runtime.

## Advanced setup

The companion executable still exists for a guided demo-first experience.
Cherry Studio can launch it directly with:

```text
command: /path/to/traceloom
arguments: mcp --demo
```

Companion smoke:

```bash
traceloom mcp --demo --print-tools
```

## Public docs

- [Getting Started](docs/guide/en/getting-started.md)
- [Cherry Studio Guide](docs/guide/en/cherry-studio.md)
- [CLI Guide](docs/guide/en/cli.md)
- [Example Matrix And Playbooks](docs/guide/en/examples.md)
- [MCP Guide](docs/guide/en/mcp.md)
- [Schema Guide](docs/guide/en/schema.md)
- [Roadmap Guide](docs/guide/en/roadmap.md)

## Repository layout

- `traceloom/`: protocol runtime, validator, query layer, workflow/navigation, MCP wrapper, and CLI
- `tests/`: regression coverage for parsing, validation, CLI, MCP, workspace/bootstrap, and docs surface
- `examples/`: golden-path, versioned, and invalid artifact repositories
- `templates/minimal-requirement-repo/`: minimal `Brief`-first workspace template
- `templates/starter-repo/`: full six-artifact starter template
- `docs/guide/`: public usage guides

## Implementation source of truth

- structured implementation rules live in [04_schema_v1.yaml](04_schema_v1.yaml)
- if narrative guidance and runtime rules diverge, follow [04_schema_v1.yaml](04_schema_v1.yaml)
- the packaged runtime copy also lives at [traceloom/resources/04_schema_v1.yaml](traceloom/resources/04_schema_v1.yaml)
