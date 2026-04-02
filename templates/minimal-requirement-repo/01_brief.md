---
artifact_id: BRIEF-TEMPLATE-001
artifact_type: brief
title: Starter Requirement Brief
summary: Replace this summary with the current requirement slice your team is clarifying.
status: draft
version: v0.1
owner:
  actor_id: user:starter.pm
  role: pm
  display_name: Starter PM
created_at: "2026-04-02T09:00:00+08:00"
updated_at: "2026-04-02T09:00:00+08:00"
scope:
  product_area: starter
  feature_key: starter-feature
  in_scope:
    - Clarify one current requirement slice
    - Establish the first governed baseline for that slice
  out_of_scope:
    - Full lifecycle planning
    - Hosted runtime setup
---

## Background

Describe the user or business context behind the current requirement.

## Problem Statement

Describe the immediate delivery problem that needs clarification.

## Target Users

- Product managers shaping the current slice
- Engineering partners preparing for design handoff

## Goals

- Produce a brief that is sufficient to seed PRD shaping

## Success Metrics

- The team can decide whether the slice is still `brief_only` or ready for `PRD`

## Non-goals

- Cover every downstream artifact before the requirement is stable

## Trace Units

```yaml
- id: GOAL-001
  type: GOAL
  title: Establish a governed requirement baseline
  statement: The current requirement slice should become clear enough to seed PM review and PRD shaping.
  status: proposed
  priority: high
  success_measure: The brief is explicit enough to identify missing evidence and next handoff conditions.
```

## Relation Edges

```yaml
[]
```
