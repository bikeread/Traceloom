---
artifact_id: TEST-2026-001
artifact_type: test_acceptance
title: User Tag Bulk Import Test & Acceptance
summary: Verify preview-before-commit behavior, validation output, and commit correctness for staged CSV imports.
status: done
version: v0.1
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
created_at: "2026-03-23T13:00:00+08:00"
updated_at: "2026-03-23T18:00:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - preview-before-commit behavior
    - row validation
    - commit correctness
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
  - target_id: DESIGN-2026-001
    target_kind: artifact
    relation_type: references
    target_type: solution_design
review_records:
  - reviewer:
      actor_id: user:li.pm
      role: pm
      display_name: Li PM
    decision: approve
    recorded_at: "2026-03-23T13:45:00+08:00"
    related_transition: in_review->approved
  - reviewer:
      actor_id: user:zhou.tl
      role: tech_lead
      display_name: Zhou TL
    decision: approve
    recorded_at: "2026-03-23T13:50:00+08:00"
    related_transition: in_review->approved
status_history:
  - from_status: in_review
    to_status: approved
    changed_at: "2026-03-23T14:00:00+08:00"
    changed_by:
      actor_id: user:qin.qa
      role: qa
      display_name: Qin QA
  - from_status: approved
    to_status: active
    changed_at: "2026-03-23T14:15:00+08:00"
    changed_by:
      actor_id: user:qin.qa
      role: qa
      display_name: Qin QA
  - from_status: active
    to_status: done
    changed_at: "2026-03-23T18:00:00+08:00"
    changed_by:
      actor_id: user:qin.qa
      role: qa
      display_name: Qin QA
change_summary:
  - Initial end-to-end example test artifact
open_questions: []
tags:
  - example
  - test
  - user-tag-bulk-import
---

## Test Scope

- CSV upload with valid rows
- CSV upload with malformed rows
- Commit after successful preview

## Coverage Matrix

- `AC-001` is verified by `TC-001`.

## Test Cases

- Upload a valid CSV and confirm preview results appear before commit.
- Upload a CSV with malformed rows and confirm row-level errors are shown.
- Confirm that tags are not applied until commit is confirmed.

## Regression Scope

- Existing single-user tag editing
- Existing tag dictionary lookup

## Trace Units

```yaml
- id: TC-001
  type: TC
  title: Verify preview before tag commit
  statement: Upload a valid CSV, confirm preview and validation output, and verify that no user tag changes happen until the commit action succeeds.
  status: done
  priority: critical
  method: manual-plus-api
  expected_result: Preview data appears before commit, invalid rows are reported, and committed rows update user tags only after confirmation.
```

## Relation Edges

```yaml
- edge_id: EDGE-0006
  relation_type: verifies
  from:
    id: AC-001
    kind: trace_unit
    artifact_id: PRD-2026-001
    type: AC
  to:
    id: TC-001
    kind: trace_unit
    artifact_id: TEST-2026-001
    type: TC
```
