---
artifact_id: TEST-2026-002
artifact_type: test_acceptance
title: User Tag Bulk Import Test & Acceptance v0.2
summary: Verify retry-safe commit behavior and preserved preview context for staged CSV imports.
status: draft
version: v0.2
owner:
  actor_id: user:qin.qa
  role: qa
  display_name: Qin QA
reviewers:
  - actor_id: user:li.pm
    role: pm
    display_name: Li PM
  - actor_id: user:zhou.tl
    role: tech_lead
    display_name: Zhou TL
created_at: "2026-03-24T09:45:00+08:00"
updated_at: "2026-03-24T09:45:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - retry-safe commit behavior
    - preserved preview context
    - validation output
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
  - target_id: DESIGN-2026-002
    target_kind: artifact
    relation_type: references
    target_type: solution_design
review_records: []
status_history: []
change_summary:
  - Supersedes v0.1 test artifact with retry-safe commit coverage
open_questions: []
tags:
  - example
  - test
  - versioned
  - user-tag-bulk-import
---

## Test Scope

- CSV upload with valid rows
- Retry after transient commit failure
- Commit after successful preview recovery

## Coverage Matrix

- `AC-002` is verified by `TC-002`.

## Test Cases

- Trigger a transient commit failure and confirm preview context remains available for retry.
- Retry the commit without re-uploading the CSV and confirm successful tag application.
- Confirm invalid rows remain visible across retry attempts.

## Regression Scope

- Existing single-user tag editing
- Existing tag dictionary lookup

## Trace Units

```yaml
- id: TC-002
  type: TC
  title: Verify retry-safe commit behavior
  statement: Trigger a transient commit failure, confirm preview state remains available, and verify a retry succeeds without re-uploading the CSV.
  status: proposed
  priority: critical
  method: manual-plus-api
  expected_result: Preview context survives transient failures, invalid rows remain visible, and a retry can commit valid rows without a new upload.
```

## Relation Edges

```yaml
- edge_id: EDGE-2009
  relation_type: verifies
  from:
    id: AC-002
    kind: trace_unit
    artifact_id: PRD-2026-002
    type: AC
  to:
    id: TC-002
    kind: trace_unit
    artifact_id: TEST-2026-002
    type: TC

- edge_id: EDGE-2010
  relation_type: supersedes
  from:
    id: TEST-2026-002
    kind: artifact
    type: test_acceptance
  to:
    id: TEST-2026-001
    kind: artifact
    type: test_acceptance
```
