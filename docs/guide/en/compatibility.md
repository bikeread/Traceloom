# Compatibility Guide

English | [简体中文](../zh-CN/compatibility.md)

This guide describes the current support boundaries for the Traceloom public beta.

## Supported client story

- canonical product surface: Traceloom MCP
- first official recommended client: Cherry Studio
- secondary path: other MCP-capable IDEs and local AI tools using the same read-only server command

## Supported baseline

- companion executable is the primary no Python first-run path
- Python `3.10+` is only required for source-checkout fallback
- local installation from a checked-out repository with `python -m pip install .`
- installed `traceloom` CLI is the primary outsider path for public-beta evaluation
- `python -m traceloom` is fallback-only for constrained shells or contributor workflows
- local read-only MCP usage against repositories that follow the Traceloom artifact model
- local governed write helpers through the CLI for draft creation, draft revision, artifact supersession, review decisions, validation records, and status promotion

## Known limits

- no public write-side MCP operations yet
- no hosted SaaS or managed sync service
- public-beta guidance is strongest for the bundled examples, the starter template, and Cherry Studio

## What is stable enough to evaluate

- feature triage
- release triage
- impact analysis
- version-aware read/query behavior
- local governed write helpers for the current narrow Track A slice, including draft/version lifecycle writes

## What to treat as still evolving

- broader client-specific setup guides beyond Cherry Studio
- write-side workflow automation beyond the local CLI helpers
- packaging and install ergonomics beyond the documented companion-executable path
