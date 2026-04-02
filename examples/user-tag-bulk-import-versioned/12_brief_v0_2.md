---
artifact_id: BRIEF-2026-002
artifact_type: brief
title: User Tag Bulk Import Brief v0.2
summary: Clarify the original batch tag import brief with retry-safe operator guidance and rollout support expectations.
status: draft
version: v0.2
owner:
  actor_id: user:li.pm
  role: pm
  display_name: Li PM
reviewers:
  - actor_id: user:zhou.tl
    role: tech_lead
    display_name: Zhou TL
created_at: "2026-03-24T09:00:00+08:00"
updated_at: "2026-03-24T09:00:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - CSV-based user tag import for operations staff
    - Preview before commit
    - Retry-safe operator guidance after transient failures
  out_of_scope:
    - Scheduled recurring imports
    - Third-party CRM sync
  target_release: "2026.04"
  target_iteration: sprint-18
  target_platforms:
    - admin_web
downstream_refs:
  - target_id: PRD-2026-002
    target_kind: artifact
    relation_type: derived_from
    target_type: prd_story_pack
review_records: []
status_history: []
change_summary:
  - Supersedes v0.1 brief with retry-safe operator guidance and rollout support expectations
open_questions: []
tags:
  - example
  - brief
  - versioned
  - user-tag-bulk-import
---

## Background

Operations staff still need batch tag import, but the first rollout showed that transient commit failures create confusion unless the handoff explicitly describes retry-safe operator behavior.

## Problem Statement

The original brief captured the batch import need, but it did not make retry-safe operator guidance and support handoff expectations explicit enough for the next iteration.

## Target Users

- Growth operations specialists
- Support leads preparing campaign lists

## Goals

- Preserve the original bulk-tagging efficiency gain
- Make transient failure handling understandable for operators and support

## Success Metrics

- 5,000-row import can still be completed in under 10 minutes
- Operators can retry transient commit failures without re-uploading the CSV

## Non-goals

- Full customer data import
- Automatic tag rule scheduling

## Trace Units

```yaml
- id: GOAL-002
  type: GOAL
  title: Preserve efficiency with retry-safe operator handling
  statement: Batch tag assignment should remain fast while giving operators and support clear retry-safe handling when transient commit failures happen.
  status: proposed
  priority: critical
  success_measure: Operators can recover from a transient commit failure without restarting the import flow or escalating to engineering.
```

## Relation Edges

```yaml
- edge_id: EDGE-3001
  relation_type: supersedes
  from:
    id: BRIEF-2026-002
    kind: artifact
    type: brief
  to:
    id: BRIEF-2026-001
    kind: artifact
    type: brief
```
