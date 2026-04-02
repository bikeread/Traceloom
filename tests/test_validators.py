from pathlib import Path
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


def write_markdown(root: Path, filename: str, content: str) -> None:
    (root / filename).write_text(textwrap.dedent(content), encoding="utf-8")


class ValidatorCoverageTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.repository import load_repository
            from traceloom.validators import load_schema, validate_repository
        except ImportError as exc:
            self.fail(f"could not import validator runtime: {exc}")
        return load_repository, load_schema, validate_repository

    def test_validate_repository_reports_invalid_trace_unit_shape(self):
        load_repository, load_schema, validate_repository = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_markdown(
                root,
                "01_brief.md",
                """\
                ---
                artifact_id: BRIEF-TEST-001
                artifact_type: brief
                title: Broken Brief
                summary: Broken brief for trace-unit validator coverage.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: pm
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: broken-trace-unit
                  in_scope:
                    - validator coverage
                ---

                ## Background

                Example background.

                ## Problem Statement

                Example problem.

                ## Target Users

                Example target user.

                ## Goals

                Example goal.

                ## Success Metrics

                Example metric.

                ## Non-goals

                Example non-goal.

                ## Trace Units

                ```yaml
                - id: goal-010
                  type: GOAL
                  title: Example goal
                  statement: Example goal statement.
                ```
                """,
            )

            repository = load_repository([root])
            issues = validate_repository(repository, schema)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("goal-010" in message and "pattern" in message for message in messages))
        self.assertTrue(any("success_measure" in message for message in messages))

    def test_validate_repository_reports_invalid_relation_edge_consistency(self):
        load_repository, load_schema, validate_repository = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_markdown(
                root,
                "01_brief.md",
                """\
                ---
                artifact_id: BRIEF-TEST-001
                artifact_type: brief
                title: Brief
                summary: Example brief.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: pm
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: relation-edge-check
                  in_scope:
                    - validator coverage
                ---

                ## Background

                Example background.

                ## Problem Statement

                Example problem.

                ## Target Users

                Example target user.

                ## Goals

                Example goal.

                ## Success Metrics

                Example metric.

                ## Non-goals

                Example non-goal.

                ## Trace Units

                ```yaml
                - id: GOAL-010
                  type: GOAL
                  title: Example goal
                  statement: Example goal statement.
                  success_measure: Example metric.
                ```
                """,
            )
            write_markdown(
                root,
                "02_prd.md",
                """\
                ---
                artifact_id: PRD-TEST-001
                artifact_type: prd_story_pack
                title: PRD
                summary: Example PRD.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: pm
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: relation-edge-check
                  in_scope:
                    - validator coverage
                ---

                ## User Scenarios

                Example scenario.

                ## Scope In

                Example in scope.

                ## Scope Out

                Example out of scope.

                ## Functional Requirements

                Example requirement.

                ## Edge Cases

                Example edge case.

                ## Acceptance Criteria

                Example acceptance criterion.

                ## Trace Units

                ```yaml
                - id: REQ-010
                  type: REQ
                  title: Example requirement
                  statement: Example requirement statement.
                  rationale: Example rationale.
                ```

                ## Relation Edges

                ```yaml
                - edge_id: EDGE-1010
                  relation_type: invalid_link
                  from:
                    id: GOAL-010
                    kind: trace_unit
                    artifact_id: PRD-TEST-001
                    type: REQ
                  to:
                    id: REQ-010
                    kind: trace_unit
                    artifact_id: PRD-TEST-001
                    type: REQ
                ```
                """,
            )

            repository = load_repository([root])
            issues = validate_repository(repository, schema)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("relation_type" in message and "invalid_link" in message for message in messages))
        self.assertTrue(any("EDGE-1010" in message and "type" in message and "GOAL" in message and "REQ" in message for message in messages))
        self.assertTrue(any("EDGE-1010" in message and "artifact_id" in message and "BRIEF-TEST-001" in message for message in messages))

    def test_validate_repository_reports_typed_ref_target_type_mismatch(self):
        load_repository, load_schema, validate_repository = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_markdown(
                root,
                "01_brief.md",
                """\
                ---
                artifact_id: BRIEF-TEST-001
                artifact_type: brief
                title: Brief
                summary: Example brief.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: pm
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: typed-ref-check
                  in_scope:
                    - validator coverage
                downstream_refs:
                  - target_id: PRD-TEST-001
                    target_kind: artifact
                    relation_type: derived_from
                    target_type: solution_design
                ---

                ## Background

                Example background.

                ## Problem Statement

                Example problem.

                ## Target Users

                Example target user.

                ## Goals

                Example goal.

                ## Success Metrics

                Example metric.

                ## Non-goals

                Example non-goal.

                ## Trace Units

                ```yaml
                - id: GOAL-010
                  type: GOAL
                  title: Example goal
                  statement: Example goal statement.
                  success_measure: Example metric.
                ```
                """,
            )
            write_markdown(
                root,
                "02_prd.md",
                """\
                ---
                artifact_id: PRD-TEST-001
                artifact_type: prd_story_pack
                title: PRD
                summary: Example PRD.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: pm
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: typed-ref-check
                  in_scope:
                    - validator coverage
                ---

                ## User Scenarios

                Example scenario.

                ## Scope In

                Example in scope.

                ## Scope Out

                Example out of scope.

                ## Functional Requirements

                Example requirement.

                ## Edge Cases

                Example edge case.

                ## Acceptance Criteria

                Example acceptance criterion.

                ## Trace Units

                ```yaml
                - id: REQ-010
                  type: REQ
                  title: Example requirement
                  statement: Example requirement statement.
                  rationale: Example rationale.
                ```
                """,
            )

            repository = load_repository([root])
            issues = validate_repository(repository, schema)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("target_type" in message and "solution_design" in message and "prd_story_pack" in message for message in messages))

    def test_validate_repository_reports_invalid_nested_header_objects(self):
        load_repository, load_schema, validate_repository = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_markdown(
                root,
                "01_brief.md",
                """\
                ---
                artifact_id: BRIEF-TEST-001
                artifact_type: brief
                title: Brief
                summary: Example brief.
                status: draft
                version: v0.1
                owner:
                  actor_id: user:test.pm
                  role: product_manager
                created_at: "2026-03-23T09:00:00+08:00"
                updated_at: "2026-03-23T09:00:00+08:00"
                scope:
                  product_area: growth
                  feature_key: nested-header-check
                  in_scope: validator coverage
                ---

                ## Background

                Example background.

                ## Problem Statement

                Example problem.

                ## Target Users

                Example target user.

                ## Goals

                Example goal.

                ## Success Metrics

                Example metric.

                ## Non-goals

                Example non-goal.

                ## Trace Units

                ```yaml
                - id: GOAL-010
                  type: GOAL
                  title: Example goal
                  statement: Example goal statement.
                  success_measure: Example metric.
                ```
                """,
            )

            repository = load_repository([root])
            issues = validate_repository(repository, schema)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("role" in message and "product_manager" in message for message in messages))
        self.assertTrue(any("in_scope" in message and "list[string]" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
