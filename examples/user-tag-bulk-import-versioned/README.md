# User Tag Bulk Import Versioned Example

This example extends the minimal end-to-end Traceloom flow for `user-tag-bulk-import` with a committed multi-version artifact-family example.

Artifacts included:

1. `01_brief.md`
2. `02_prd.md`
3. `03_solution_design.md`
4. `04_execution_plan.md`
5. `05_test_acceptance.md`
6. `06_release_review.md`
7. `07_release_review_v0_2.md`
8. `08_prd_v0_2.md`
9. `09_solution_design_v0_2.md`
10. `10_execution_plan_v0_2.md`
11. `11_test_acceptance_v0_2.md`
12. `12_brief_v0_2.md`

Core requirement-to-release chain demonstrated:

`GOAL-001 -> REQ-001 -> DEC-001 -> TASK-001 -> REL-001 -> REV-001`

Acceptance and verification branch demonstrated:

`REQ-001 -> AC-001 -> TC-001`

Additional coverage demonstrated:

- `GOAL-001 -> REQ-001`
- `REQ-001 -> AC-001`
- `NFR-001 -> DEC-001`
- `AC-001 -> TC-001`
- `DEC-001 -> TASK-001`
- `REQ-001 -> REL-001`
- `TASK-001 -> REL-001`
- `GOAL-001 -> REV-001`
- `REL-001 -> REV-001`

Version lineage demonstrated:

- `BRIEF-2026-002 (v0.2)` artifact-level `supersedes` -> `BRIEF-2026-001 (v0.1)`
- `PRD-2026-002 (v0.2)` artifact-level `supersedes` -> `PRD-2026-001 (v0.1)`
- `DESIGN-2026-002 (v0.2)` artifact-level `supersedes` -> `DESIGN-2026-001 (v0.1)`
- `EXEC-2026-002 (v0.2)` artifact-level `supersedes` -> `EXEC-2026-001 (v0.1)`
- `TEST-2026-002 (v0.2)` artifact-level `supersedes` -> `TEST-2026-001 (v0.1)`
- `RELEASE-2026-002 (v0.2)` artifact-level `supersedes` -> `RELEASE-2026-001 (v0.1)`
- successor v0.2 artifacts now form a complete `GOAL-002 -> REQ-002 -> DEC-002 -> TASK-002 -> TC-002 -> REL-002 -> REV-002` replacement flow
