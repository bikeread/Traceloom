---
artifact_id: BRIEF-2026-001
artifact_type: brief
title: User Tag Bulk Import Brief
summary: Enable operations staff to import user tags in batches instead of editing tags one user at a time.
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
created_at: "2026-03-23T09:00:00+08:00"
updated_at: "2026-03-23T18:00:00+08:00"
scope:
  product_area: growth
  feature_key: user-tag-bulk-import
  in_scope:
    - CSV-based user tag import for operations staff
    - Preview before commit
  out_of_scope:
    - Scheduled recurring imports
    - Third-party CRM sync
  target_release: "2026.04"
  target_iteration: sprint-18
  target_platforms:
    - admin_web
downstream_refs:
  - target_id: PRD-2026-001
    target_kind: artifact
    relation_type: derived_from
    target_type: prd_story_pack
review_records:
  - reviewer:
      actor_id: user:li.pm
      role: pm
      capability: pm
      display_name: Li PM
    decision: approve
    recorded_at: "2026-03-23T09:40:00+08:00"
    related_transition: in_review->approved
status_history:
  - from_status: in_review
    to_status: approved
    changed_at: "2026-03-23T09:45:00+08:00"
    changed_by:
      actor_id: user:zhou.tl
      role: tech_lead
      display_name: Zhou TL
  - from_status: approved
    to_status: active
    changed_at: "2026-03-23T10:00:00+08:00"
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
  - Initial end-to-end example brief
open_questions: []
tags:
  - example
  - brief
  - user-tag-bulk-import
---

## Background

Operations staff currently add user tags one account at a time. This blocks campaign setup when thousands of users need the same tagging rule.

## Problem Statement

The current workflow is too slow, too manual, and too error-prone for batch growth operations.

## Target Users

- Growth operations specialists
- Support leads preparing campaign lists

## Goals

- Reduce bulk tagging time from hours to minutes
- Reduce manual tagging mistakes during campaigns

## Success Metrics

- 5,000-row import can be completed in under 10 minutes
- Validation catches malformed rows before commit

## Non-goals

- Full customer data import
- Automatic tag rule scheduling

## Trace Units

```yaml
- id: GOAL-001
  type: GOAL
  title: Reduce bulk tagging effort
  statement: Bulk tag assignment should be executable without manual one-by-one editing.
  status: done
  priority: critical
  success_measure: Operations can complete a 5,000-row import in under 10 minutes with less than 1% corrected rows after validation.
```
