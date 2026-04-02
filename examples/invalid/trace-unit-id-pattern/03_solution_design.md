---
artifact_id: DESIGN-2026-001
artifact_type: solution_design
title: User Tag Bulk Import Solution Design
summary: Implement a staged CSV import flow with parse-preview-commit separation to support validation before tag updates.
status: done
version: v0.1
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
created_at: "2026-03-23T11:00:00+08:00"
updated_at: "2026-03-23T18:00:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - staged parsing
    - preview before commit
    - commit endpoint
  out_of_scope:
    - recurring imports
  target_release: "2026.04"
  target_iteration: sprint-18
  target_platforms:
    - admin_web
upstream_refs:
  - target_id: PRD-2026-001
    target_kind: artifact
    relation_type: derived_from
    target_type: prd_story_pack
downstream_refs:
  - target_id: EXEC-2026-001
    target_kind: artifact
    relation_type: references
    target_type: execution_plan
review_records:
  - reviewer:
      actor_id: user:li.pm
      role: pm
      display_name: Li PM
    decision: approve
    recorded_at: "2026-03-23T11:40:00+08:00"
    related_transition: in_review->approved
  - reviewer:
      actor_id: user:sun.dev
      role: developer
      display_name: Sun Dev
    decision: approve
    recorded_at: "2026-03-23T11:45:00+08:00"
    related_transition: in_review->approved
status_history:
  - from_status: in_review
    to_status: approved
    changed_at: "2026-03-23T12:00:00+08:00"
    changed_by:
      actor_id: user:zhou.tl
      role: tech_lead
      display_name: Zhou TL
  - from_status: approved
    to_status: active
    changed_at: "2026-03-23T12:15:00+08:00"
    changed_by:
      actor_id: user:zhou.tl
      role: tech_lead
      display_name: Zhou TL
  - from_status: active
    to_status: done
    changed_at: "2026-03-23T18:00:00+08:00"
    changed_by:
      actor_id: user:zhou.tl
      role: tech_lead
      display_name: Zhou TL
change_summary:
  - Initial end-to-end example design
open_questions: []
tags:
  - example
  - design
  - user-tag-bulk-import
---

## Solution Summary

Use a two-phase import flow:

1. upload and parse into a staging area
2. show preview and validation results
3. apply tag changes only after explicit commit

## Affected Components

- Admin upload UI
- Import API
- Validation service
- Staging table for parsed rows

## Decisions

The import will not write user tags during file upload. Upload only creates a staging batch and preview summary.

## Coverage Map

- `REQ-001` is covered by staged upload plus explicit commit.
- `NFR-001` is covered by bulk parsing and a staging table optimized for preview queries.

## Risks

- Large invalid files could slow preview generation.
- Partial commit behavior could confuse operations staff if preview and commit use different rules.

## Rollback Considerations

If commit fails, no staged batch should be marked as applied. Operators can re-run the import after fixing the issue.

## Trace Units

```yaml
- id: DEC-001
  type: DEC
  title: Stage rows before commit
  statement: The system will parse uploaded CSV rows into a staging batch, generate a preview, and only apply user tags after an explicit commit action.
  status: done
  priority: critical
  rationale: This guarantees preview-before-commit behavior and keeps validation separate from irreversible writes.

- id: RISK-001
  type: RISK
  title: Slow preview on malformed files
  statement: Very large or malformed CSV files may degrade preview generation time.
  status: done
  priority: high
  impact: Operators may abandon the workflow if feedback is too slow.
  mitigation: Reject unsupported files early and use batch-level preview queries.
```

## Relation Edges

```yaml
- edge_id: EDGE-0003
  relation_type: covers
  from:
    id: REQ-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: REQ
  to:
    id: DEC-001
    kind: trace_unit
    artifact_id: DESIGN-2026-001
    type: DEC

- edge_id: EDGE-0004
  relation_type: covers
  from:
    id: NFR-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: NFR
  to:
    id: DEC-001
    kind: trace_unit
    artifact_id: DESIGN-2026-001
    type: DEC
```
