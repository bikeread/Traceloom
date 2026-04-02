---
artifact_id: PRD-2026-001
artifact_type: prd_story_pack
title: User Tag Bulk Import PRD
summary: Define the CSV import workflow, validation rules, and acceptance criteria for batch user tag assignment.
status: done
version: v0.1
owner:
  actor_id: user:li.pm
  role: pm
  display_name: Li PM
reviewers:
  - actor_id: user:zhou.tl
    role: tech_lead
    display_name: Zhou TL
  - actor_id: user:qin.qa
    role: qa
    display_name: Qin QA
created_at: "2026-03-23T10:00:00+08:00"
updated_at: "2026-03-23T18:00:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - CSV upload
    - Preview before commit
    - Validation error reporting
  out_of_scope:
    - Scheduled imports
    - Non-CSV formats
  target_release: "2026.04"
  target_iteration: sprint-18
  target_platforms:
    - admin_web
upstream_refs:
  - target_id: BRIEF-2026-001
    target_kind: artifact
    relation_type: derived_from
    target_type: brief
downstream_refs:
  - target_id: DESIGN-2026-001
    target_kind: artifact
    relation_type: references
    target_type: solution_design
  - target_id: TEST-2026-001
    target_kind: artifact
    relation_type: references
    target_type: test_acceptance
review_records:
  - reviewer:
      actor_id: user:zhou.tl
      role: tech_lead
      capability: tech_lead
      display_name: Zhou TL
    decision: approve
    recorded_at: "2026-03-23T10:45:00+08:00"
    related_transition: in_review->approved
  - reviewer:
      actor_id: user:qin.qa
      role: qa
      capability: qa
      display_name: Qin QA
    decision: approve
    recorded_at: "2026-03-23T10:50:00+08:00"
    related_transition: in_review->approved
status_history:
  - from_status: in_review
    to_status: approved
    changed_at: "2026-03-23T11:00:00+08:00"
    changed_by:
      actor_id: user:li.pm
      role: pm
      display_name: Li PM
  - from_status: approved
    to_status: active
    changed_at: "2026-03-23T11:15:00+08:00"
    changed_by:
      actor_id: user:li.pm
      role: pm
      display_name: Li PM
  - from_status: active
    to_status: done
    changed_at: "2026-03-23T18:00:00+08:00"
    changed_by:
      actor_id: user:li.pm
      role: pm
      display_name: Li PM
change_summary:
  - Initial end-to-end example PRD
open_questions: []
tags:
  - example
  - prd
  - user-tag-bulk-import
---

## User Scenarios

An operations specialist uploads a CSV containing `user_id` and `tag_code`, reviews a preview, fixes invalid rows, and then commits the import.

## Scope In

- Upload CSV file
- Parse rows and validate required columns
- Show preview counts and row-level errors
- Commit valid rows only after explicit confirmation

## Scope Out

- Automatic rollback of previous imports
- Background scheduling

## Functional Requirements

- The system must accept a CSV file with `user_id` and `tag_code`.
- The system must validate rows before applying any tag changes.
- The system must show a preview summary before the import is committed.

## Non-functional Requirements

- Preview generation must finish within 30 seconds for a 5,000-row file.

## Edge Cases

- Duplicate rows for the same user and tag
- Unknown tag code
- Missing user ID

## Acceptance Criteria

- Valid CSV upload produces a preview with valid-row count, invalid-row count, and row-level errors before commit.

## Trace Units

```yaml
- id: REQ-001
  type: REQ
  title: Import user tags from CSV
  statement: The system shall allow operations staff to upload a CSV file and apply user tags in batch after preview confirmation.
  status: done
  priority: critical
  rationale: This replaces slow and error-prone manual tagging.

- id: NFR-001
  type: NFR
  title: Preview performance
  statement: Preview generation for a 5,000-row CSV should complete within 30 seconds.
  status: done
  priority: high
  quality_attribute: performance
  target: 30 seconds for 5,000 rows

- id: AC-001
  type: AC
  title: Preview before commit
  statement: A valid CSV upload must produce a preview with validation results before any tag changes are committed.
  status: done
  priority: critical
  verification_hint: Verify that upload alone does not change user tags and that preview data is shown before confirmation.
```

## Relation Edges

```yaml
- edge_id: EDGE-0001
  relation_type: refines
  from:
    id: GOAL-001
    kind: trace_unit
    artifact_id: BRIEF-2026-001
    type: GOAL
  to:
    id: REQ-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: REQ

- edge_id: EDGE-0002
  relation_type: refines
  from:
    id: REQ-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: REQ
  to:
    id: AC-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: AC
```
