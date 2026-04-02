---
artifact_id: BRIEF-TEMPLATE-001
artifact_type: brief
title: Starter Feature Brief
summary: Replace this summary with the outcome your team wants to achieve.
status: in_review
version: v0.1
owner:
  actor_id: user:starter.pm
  role: pm
  display_name: Starter PM
created_at: "2026-03-27T09:00:00+08:00"
updated_at: "2026-03-27T09:00:00+08:00"
scope:
  product_area: starter
  feature_key: starter-feature
  in_scope:
    - Bootstrap a single starter feature slice
    - Establish a governed baseline for PM, engineering, and QA
  out_of_scope:
    - Multi-feature portfolio planning
    - Hosted runtime setup
  target_release: "2026.05"
downstream_refs:
  - target_id: PRD-TEMPLATE-001
    target_kind: artifact
    relation_type: derived_from
    target_type: prd_story_pack
---

## Background

Describe the user or business problem.

## Problem Statement

Describe the current pain that blocks delivery.

## Target Users

- Product managers coordinating the slice
- Engineering and QA partners consuming the baseline

## Goals

- Produce a single governed baseline for the starter feature

## Success Metrics

- The team can move from brief into PRD review without rewriting context from scratch

## Non-goals

- Cover every project in the organization

## Trace Units

```yaml
- id: GOAL-001
  type: GOAL
  title: Establish a governed starter baseline
  statement: The starter feature should begin with a brief that product, engineering, and QA can all work from.
  status: proposed
  priority: high
  success_measure: The starter brief is sufficient to seed a PRD and handoff discussion.
```

## Relation Edges

```yaml
[]
```
