# Cherry Studio Guide

English | [简体中文](../zh-CN/cherry-studio.md)

Cherry Studio is the first official recommended client for the Traceloom public beta.
This guide stays tightly focused on `Path 1: Evaluate Traceloom`.

## Path 1: Evaluate Traceloom

Use this path when you want the fastest first run with the least setup.

- install Cherry Studio locally
- get the Traceloom companion executable
- connect Cherry Studio to that companion executable
- launch `mcp --demo`
- keep the session read-only and use it to evaluate the bundled demo

Cherry Studio configuration for the companion executable path:

```text
command: /path/to/traceloom
arguments: mcp --demo
```

This is the supported no Python first run.
If your team already shared a companion build with you, use that copy directly.
If you do not have a companion build yet, open the latest successful `Build Companion Executable` workflow run, download the artifact for your platform, and use the `traceloom` executable inside that downloaded bundle.
This workflow-run download path is the current evaluator fallback before formal release artifacts exist.
If you still cannot use that workflow-run build, use the source-checkout fallback in [Getting Started](getting-started.md).

## Ask the three readiness questions

Ask Cherry Studio to call the Traceloom MCP server for these canonical question flows:

- feature triage: "Is this feature ready to move forward?"
- release triage: "Is this release ready?"
- impact analysis: "What does this change affect?"

Expected outcomes:

- a readiness judgment you can explain
- blockers and missing evidence you can act on
- impact context that stays grounded in repository artifacts

## Path 2: Start a Real Requirement

This guide stops after the evaluation path.
When the demo proves useful and you want to move into real work, switch to `Path 2: Start a Real Requirement`.

That handoff should stay PM-facing:

- start from the current requirement
- add optional supporting inputs only when they sharpen the slice
- generate the first baseline
- review open questions and the next recommended step

Use [Getting Started](getting-started.md) as the path selector and [MCP Guide](mcp.md) if you need the read-only contract details.

## After the first run

- [Getting Started](getting-started.md) for the broader two-path entry
- [MCP Guide](mcp.md) for the public read-only contract
