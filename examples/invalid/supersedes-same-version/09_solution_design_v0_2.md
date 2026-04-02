---
artifact_id: DESIGN-2026-002
artifact_type: solution_design
title: User Tag Bulk Import Solution Design v0.2
summary: Extend the staged import design with retry-safe commit handling and preserved preview context.
status: draft
version: v0.2
owner:
  actor_id: user:zhou.tl
  role: tech_lead
  display_name: Zhou TL
reviewers:
  - actor_id: user:li.pm
    role: pm
    display_name: Li PM
  - actor_id: user:sun.dev
    role: developer
    display_name: Sun Dev
created_at: "2026-03-24T09:15:00+08:00"
updated_at: "2026-03-24T09:15:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - staged parsing
    - preview before commit
    - retry-safe commit handling
  out_of_scope:
    - recurring imports
  target_release: "2026.04"
  target_iteration: sprint-18
  target_platforms:
    - admin_web
upstream_refs:
  - target_id: PRD-2026-002
    target_kind: artifact
    relation_type: derived_from
    target_type: prd_story_pack
downstream_refs:
  - target_id: EXEC-2026-002
    target_kind: artifact
    relation_type: references
    target_type: execution_plan
review_records: []
status_history: []
change_summary:
  - Supersedes v0.1 design with retry-safe commit handling
open_questions: []
tags:
  - example
  - design
  - versioned
  - user-tag-bulk-import
---

## Solution Summary

Use the same parse-preview-commit flow as v0.1, but keep preview state available for safe retries after transient commit failures.

## Affected Components

- Admin upload UI
- Import API
- Validation service
- Staging table for parsed rows
- Retry token and preview-state retention logic

## Decisions

The import keeps preview context attached to the staging batch long enough for an operator to retry a transiently failed commit without re-uploading the CSV.

## Coverage Map

- `REQ-002` is covered by retry-safe preview-state retention plus explicit retry handling.
- `NFR-002` is covered by retained preview context and idempotent retry checks.

## Risks

- Retained preview state may increase staging storage pressure.
- Operators may retry too aggressively if failure states are not explicit.

## Rollback Considerations

If retry handling causes inconsistent state, the staging batch stays unapplied and can be discarded without touching user tags.

## Trace Units

```yaml
- id: DEC-002
  type: DEC
  title: Preserve preview state for retry-safe commits
  statement: The system will preserve preview state for a staging batch so operators can retry transient commit failures without re-uploading the CSV.
  status: proposed
  priority: critical
  rationale: Retry-safe commits reduce operator rework while keeping preview-first guarantees.

- id: RISK-002
  type: RISK
  title: Preview retention may increase storage pressure
  statement: Retaining preview state for retries may increase staging storage and cleanup complexity.
  status: proposed
  priority: high
  impact: Staging tables may grow if retry windows are too large.
  mitigation: Expire stale retry batches and cap retention windows.
```

## Relation Edges

```yaml
- edge_id: EDGE-2004
  relation_type: covers
  from:
    id: REQ-002
    kind: trace_unit
    artifact_id: PRD-2026-002
    type: REQ
  to:
    id: DEC-002
    kind: trace_unit
    artifact_id: DESIGN-2026-002
    type: DEC

- edge_id: EDGE-2005
  relation_type: covers
  from:
    id: NFR-002
    kind: trace_unit
    artifact_id: PRD-2026-002
    type: NFR
  to:
    id: DEC-002
    kind: trace_unit
    artifact_id: DESIGN-2026-002
    type: DEC

- edge_id: EDGE-2006
  relation_type: supersedes
  from:
    id: DESIGN-2026-002
    kind: artifact
    type: solution_design
  to:
    id: DESIGN-2026-001
    kind: artifact
    type: solution_design
```
