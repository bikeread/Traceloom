from pathlib import Path
import unittest

from tests.git_fixture_helpers import init_git_example_repo, replace_in_file


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class SummaryTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.repository import load_repository
            from traceloom.summaries import (
                analyze_change_impact,
                check_feature_readiness,
                check_release_readiness,
            )
            from traceloom.validators import load_schema
        except ImportError as exc:
            self.fail(f"could not import summary runtime: {exc}")
        return load_repository, load_schema, check_feature_readiness, check_release_readiness, analyze_change_impact

    def load_example_context(self):
        (
            load_repository,
            load_schema,
            check_feature_readiness,
            check_release_readiness,
            analyze_change_impact,
        ) = self.import_runtime()
        repository = load_repository([EXAMPLE_DIR])
        schema = load_schema(SCHEMA_PATH)
        return repository, schema, check_feature_readiness, check_release_readiness, analyze_change_impact

    def load_versioned_example_context(self):
        (
            load_repository,
            load_schema,
            check_feature_readiness,
            check_release_readiness,
            analyze_change_impact,
        ) = self.import_runtime()
        repository = load_repository([VERSIONED_EXAMPLE_DIR])
        schema = load_schema(SCHEMA_PATH)
        return repository, schema, check_feature_readiness, check_release_readiness, analyze_change_impact

    def test_check_feature_readiness_returns_feature_scoped_gaps_and_blockers(self):
        repository, schema, check_feature_readiness, _, _ = self.load_example_context()

        repository.artifacts_by_id["DESIGN-2026-001"].header["open_questions"] = [
            {"q_id": "Q-101", "status": "open", "note": "Need explicit rollback guidance."}
        ]
        repository.relation_edges_by_id.pop("EDGE-0006")

        summary = check_feature_readiness(repository, schema, "user-tag-bulk-import")

        self.assertEqual(summary["feature_key"], "user-tag-bulk-import")
        self.assertEqual(len(summary["artifacts"]), 6)
        self.assertEqual(summary["artifacts"][0]["artifact_id"], "BRIEF-2026-001")
        self.assertEqual([item["q_id"] for item in summary["open_questions"]], ["Q-101"])
        ac_to_tc = next(item for item in summary["coverage"] if item["upstream_type"] == "AC")
        self.assertEqual(ac_to_tc["downstream_type"], "TC")
        self.assertEqual(ac_to_tc["missing_ids"], ["AC-001"])
        self.assertIn("missing_traceability", [item["code"] for item in summary["validation_issues"]])
        blocker_kinds = {item["kind"] for item in summary["blockers"]}
        self.assertIn("open_question", blocker_kinds)
        self.assertIn("validation_issue", blocker_kinds)

    def test_check_feature_readiness_returns_golden_path_summary_for_example(self):
        repository, schema, check_feature_readiness, _, _ = self.load_example_context()

        summary = check_feature_readiness(repository, schema, "user-tag-bulk-import")

        self.assertTrue(summary["ready"])
        self.assertEqual(summary["artifact_ids"], [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
            "TEST-2026-001",
        ])
        self.assertEqual(summary["blocking_validation_issue_count"], 0)
        self.assertEqual(summary["open_question_count"], 0)
        self.assertEqual(summary["blocker_count"], 0)
        self.assertEqual(summary["validation_issues"], [])
        self.assertEqual(summary["open_questions"], [])
        self.assertEqual(
            [item["artifact_type"] for item in summary["artifact_gap_map"]],
            [
                "brief",
                "prd_story_pack",
                "solution_design",
                "execution_plan",
                "test_acceptance",
                "release_review",
            ],
        )
        self.assertTrue(all(not item["blocking_gaps"] for item in summary["artifact_gap_map"]))
        self.assertTrue(all(not item["attention_items"] for item in summary["artifact_gap_map"]))

    def test_check_feature_readiness_for_versioned_example_uses_baseline_artifacts_only(self):
        repository, schema, check_feature_readiness, _, _ = self.load_versioned_example_context()

        summary = check_feature_readiness(repository, schema, "user-tag-bulk-import")

        self.assertEqual(summary["artifact_ids"], [
            "BRIEF-2026-002",
            "DESIGN-2026-002",
            "EXEC-2026-002",
            "PRD-2026-002",
            "RELEASE-2026-002",
            "TEST-2026-002",
        ])
        self.assertEqual(summary["baseline_artifact_ids"], summary["artifact_ids"])
        self.assertEqual(summary["ambiguous_artifact_families"], [])
        self.assertTrue(summary["ready"])
        self.assertEqual(summary["blocker_count"], 0)
        self.assertEqual(
            sorted(
                artifact_id
                for item in summary["artifact_gap_map"]
                for artifact_id in item["artifact_ids"]
            ),
            summary["artifact_ids"],
        )
        self.assertNotIn("PRD-2026-001", [artifact_id for item in summary["artifact_gap_map"] for artifact_id in item["artifact_ids"]])

    def test_check_feature_readiness_maps_missing_traceability_and_open_questions_to_artifact_gap_map(self):
        repository, schema, check_feature_readiness, _, _ = self.load_example_context()

        repository.artifacts_by_id["DESIGN-2026-001"].header["open_questions"] = [
            {"q_id": "Q-101", "status": "open", "note": "Need explicit rollback guidance."}
        ]
        repository.relation_edges_by_id.pop("EDGE-0006")

        summary = check_feature_readiness(repository, schema, "user-tag-bulk-import")

        prd_entry = next(item for item in summary["artifact_gap_map"] if item["artifact_type"] == "prd_story_pack")
        design_entry = next(item for item in summary["artifact_gap_map"] if item["artifact_type"] == "solution_design")

        self.assertFalse(summary["ready"])
        self.assertTrue(
            any(
                gap["kind"] == "missing_traceability"
                and gap["trace_chain_hint"] == "AC -> TC"
                and gap["missing_ids"] == ["AC-001"]
                for gap in prd_entry["blocking_gaps"]
            )
        )
        self.assertTrue(
            any(
                item["kind"] == "open_question"
                and item["q_id"] == "Q-101"
                for item in design_entry["attention_items"]
            )
        )

    def test_check_release_readiness_returns_release_scoped_blockers(self):
        repository, schema, _, check_release_readiness, _ = self.load_example_context()

        repository.artifacts_by_id["RELEASE-2026-001"].header["open_questions"] = [
            {"q_id": "Q-201", "status": "open", "note": "Confirm rollback ownership for failed commit."}
        ]
        repository.relation_edges_by_id.pop("EDGE-0010")

        summary = check_release_readiness(repository, schema, release_target="2026.04")

        self.assertEqual(summary["release_target"], "2026.04")
        self.assertEqual(summary["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary["release_artifact_ids"], ["RELEASE-2026-001"])
        self.assertIn("RELEASE-2026-001", [item["artifact_id"] for item in summary["artifacts"]])
        self.assertEqual([item["q_id"] for item in summary["open_questions"]], ["Q-201"])
        goal_to_rev = next(
            item
            for item in summary["coverage"]
            if item["upstream_type"] == "GOAL" and item["downstream_type"] == "REV"
        )
        self.assertEqual(goal_to_rev["covered_ids"], ["GOAL-001"])
        self.assertIn("missing_traceability", [item["code"] for item in summary["validation_issues"]])
        blocker_kinds = {item["kind"] for item in summary["blockers"]}
        self.assertIn("open_question", blocker_kinds)
        self.assertIn("validation_issue", blocker_kinds)
        self.assertFalse(summary["ready"])
        self.assertGreater(summary["blocker_count"], 0)
        self.assertGreater(summary["blocking_validation_issue_count"], 0)
        self.assertEqual(summary["open_question_count"], 1)

    def test_check_release_readiness_returns_feature_scoped_golden_path_summary(self):
        repository, schema, _, check_release_readiness, _ = self.load_example_context()

        summary = check_release_readiness(repository, schema, feature_key="user-tag-bulk-import")

        self.assertTrue(summary["ready"])
        self.assertEqual(summary["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary["release_artifact_ids"], ["RELEASE-2026-001"])
        self.assertEqual(summary["artifact_ids"], [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
            "TEST-2026-001",
        ])
        self.assertEqual(summary["blocking_validation_issue_count"], 0)
        self.assertEqual(summary["open_question_count"], 0)
        self.assertEqual(summary["blocker_count"], 0)
        self.assertEqual(summary["validation_issues"], [])
        self.assertEqual(summary["open_questions"], [])

    def test_check_release_readiness_for_versioned_example_uses_baseline_artifacts_only(self):
        repository, schema, _, check_release_readiness, _ = self.load_versioned_example_context()

        summary = check_release_readiness(repository, schema, release_target="2026.04")

        self.assertEqual(summary["artifact_ids"], [
            "BRIEF-2026-002",
            "DESIGN-2026-002",
            "EXEC-2026-002",
            "PRD-2026-002",
            "RELEASE-2026-002",
            "TEST-2026-002",
        ])
        self.assertEqual(summary["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary["baseline_artifact_ids"], summary["artifact_ids"])
        self.assertEqual(summary["release_artifact_ids"], ["RELEASE-2026-002"])
        self.assertEqual(summary["ambiguous_artifact_families"], [])
        self.assertTrue(summary["ready"])
        self.assertEqual(summary["blocker_count"], 0)

    def test_check_feature_readiness_surfaces_git_backed_immutable_mutation(self):
        (
            load_repository,
            load_schema,
            check_feature_readiness,
            _,
            _,
        ) = self.import_runtime()
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        replace_in_file(
            fixture_root / "02_prd.md",
            "title: User Tag Bulk Import PRD",
            "title: User Tag Bulk Import PRD Revised In Place",
        )

        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)

        summary = check_feature_readiness(repository, schema, "user-tag-bulk-import")

        self.assertIn("immutable_artifact_mutation", [item["code"] for item in summary["validation_issues"]])
        self.assertTrue(
            any(
                item["kind"] == "validation_issue" and item["code"] == "immutable_artifact_mutation"
                for item in summary["blockers"]
            )
        )
        prd_entry = next(item for item in summary["artifact_gap_map"] if item["artifact_type"] == "prd_story_pack")
        self.assertTrue(
            any(
                gap["kind"] == "validation_issue" and gap["code"] == "immutable_artifact_mutation"
                for gap in prd_entry["blocking_gaps"]
            )
        )

    def test_analyze_change_impact_for_trace_unit_exposes_downstream_first_shape(self):
        repository, _, _, _, analyze_change_impact = self.load_example_context()

        impact = analyze_change_impact(repository, "DEC-001")

        self.assertEqual(impact["object_id"], "DEC-001")
        self.assertEqual(impact["object_kind"], "trace_unit")
        self.assertEqual(impact["owning_artifact_id"], "DESIGN-2026-001")
        self.assertEqual(impact["trace_unit_ids"], ["DEC-001"])
        self.assertEqual(impact["direct_downstream_trace_unit_ids"], ["TASK-001"])
        self.assertEqual(impact["downstream_trace_unit_ids"], ["REL-001", "REV-001", "TASK-001"])
        self.assertEqual(impact["downstream_artifact_ids"], ["EXEC-2026-001", "RELEASE-2026-001"])
        self.assertEqual(impact["direct_upstream_trace_unit_ids"], ["NFR-001", "REQ-001"])
        self.assertEqual(impact["upstream_trace_unit_ids"], ["GOAL-001", "NFR-001", "REQ-001"])
        self.assertEqual(impact["upstream_artifact_ids"], ["BRIEF-2026-001", "PRD-2026-001"])
        self.assertEqual(impact["related_artifact_ids"], [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
        ])
        self.assertEqual([edge["edge_id"] for edge in impact["related_edges"]], ["EDGE-0003", "EDGE-0004", "EDGE-0005"])

    def test_analyze_change_impact_for_artifact_exposes_seed_direct_and_transitive_context(self):
        repository, _, _, _, analyze_change_impact = self.load_example_context()

        impact = analyze_change_impact(repository, "DESIGN-2026-001")

        self.assertEqual(impact["object_id"], "DESIGN-2026-001")
        self.assertEqual(impact["object_kind"], "artifact")
        self.assertEqual(impact["owning_artifact_id"], "DESIGN-2026-001")
        self.assertEqual(impact["trace_unit_ids"], ["DEC-001", "RISK-001"])
        self.assertEqual(impact["direct_downstream_trace_unit_ids"], ["TASK-001"])
        self.assertEqual(impact["downstream_trace_unit_ids"], ["REL-001", "REV-001", "TASK-001"])
        self.assertEqual(impact["downstream_artifact_ids"], ["EXEC-2026-001", "RELEASE-2026-001"])
        self.assertEqual(impact["direct_upstream_trace_unit_ids"], ["NFR-001", "REQ-001"])
        self.assertEqual(impact["upstream_trace_unit_ids"], ["GOAL-001", "NFR-001", "REQ-001"])
        self.assertEqual(impact["upstream_artifact_ids"], ["BRIEF-2026-001", "PRD-2026-001"])
        self.assertEqual([edge["edge_id"] for edge in impact["related_edges"]], ["EDGE-0003", "EDGE-0004", "EDGE-0005"])


if __name__ == "__main__":
    unittest.main()
