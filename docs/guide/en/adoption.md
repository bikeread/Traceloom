# Adoption Guide

English | [简体中文](../zh-CN/adoption.md)

Use this guide to decide whether Traceloom fits an existing team workflow and how to evaluate that fit without overcommitting.

## Recommended evaluation path

1. Start with the bundled golden-path example.
2. Connect Cherry Studio or another MCP client to the local Traceloom server.
3. Run the three canonical question flows.
4. Compare the results with how your team currently answers the same questions.
5. Copy the starter template for a small real feature if the evaluation looks promising.

## Good fit signals

- your team already keeps important delivery context in Git and Markdown
- cross-artifact traceability matters more than rich document editing workflows
- you want local AI tooling to inspect delivery lineage without a hosted service

## Poor fit signals

- you need a hosted collaboration product first
- your source of truth lives outside Git and cannot be mirrored cleanly
- you need public write-side automation before read-side evaluation is complete

## First real adoption step

Copy `templates/starter-repo` into a sandbox repository and replace the placeholder content with one small feature slice.
Keep the first slice narrow enough that one team can review the full artifact chain in one release cycle.

## What to verify before wider rollout

- the team can keep artifact scope and IDs consistent
- the three canonical question flows stay useful on real project data
- the review burden is acceptable compared with the current process
