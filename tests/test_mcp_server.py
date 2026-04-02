import json
from pathlib import Path
import unittest

from tests.git_fixture_helpers import init_git_example_repo, replace_in_file


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
INVALID_ILLEGAL_STATUS_DIR = REPO_ROOT / "examples" / "invalid" / "illegal-status-transition"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class McpServerTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.mcp_server import build_mcp_server, dispatch_tool_call, list_registered_tools
        except ImportError as exc:
            self.fail(f"could not import MCP runtime: {exc}")
        return build_mcp_server, dispatch_tool_call, list_registered_tools

    def test_list_registered_tools_includes_atomic_and_summary_tools(self):
        _, _, list_registered_tools = self.import_runtime()

        tool_names = list_registered_tools()

        self.assertEqual(
            tool_names,
            [
                "analyze_change_impact",
                "check_design_completeness",
                "check_feature_readiness",
                "check_release_readiness",
                "diff_versions",
                "get_artifact",
                "get_delivery_slice_navigation",
                "get_artifact_workflow",
                "get_coverage",
                "get_status_history",
                "get_trace_unit",
                "list_artifact_versions",
                "list_open_questions",
                "list_related",
                "trace_downstream",
                "trace_upstream",
                "validate_repository",
            ],
        )

    def test_dispatch_tool_call_returns_json_serializable_atomic_and_summary_payloads(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        artifact_payload = dispatch_tool_call(
            "get_artifact",
            {"artifact_id": "PRD-2026-001", "view": "header"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )
        summary_payload = dispatch_tool_call(
            "check_feature_readiness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )
        validation_payload = dispatch_tool_call(
            "validate_repository",
            {},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(artifact_payload["artifact_id"], "PRD-2026-001")
        self.assertEqual(summary_payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(validation_payload["issue_count"], 0)
        json.dumps(artifact_payload, sort_keys=True)
        json.dumps(summary_payload, sort_keys=True)
        json.dumps(validation_payload, sort_keys=True)

    def test_dispatch_get_artifact_workflow_returns_gate_payload(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        payload = dispatch_tool_call(
            "get_artifact_workflow",
            {"artifact_id": "RELEASE-2026-001"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(payload["artifact_id"], "RELEASE-2026-001")
        self.assertEqual(payload["gate_id"], "release_review_gate")
        self.assertEqual(payload["current_outcome"], "approved")
        self.assertTrue(payload["controlled_transition_allowed"])
        json.dumps(payload, sort_keys=True)

    def test_dispatch_get_delivery_slice_navigation_returns_feature_payload(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        payload = dispatch_tool_call(
            "get_delivery_slice_navigation",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(payload["slice_stage"], "design_handoff_ready")
        self.assertEqual(payload["current_focus"]["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(payload["next_recommended_capability"], "tech_lead")
        json.dumps(payload, sort_keys=True)

    def test_dispatch_check_design_completeness_returns_feature_payload(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        payload = dispatch_tool_call(
            "check_design_completeness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(payload["design_artifact_id"], "DESIGN-2026-001")
        self.assertTrue(payload["ready"])
        json.dumps(payload, sort_keys=True)

    def test_dispatch_validate_repository_reports_git_backed_immutable_mutation(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        replace_in_file(
            fixture_root / "02_prd.md",
            "title: User Tag Bulk Import PRD",
            "title: User Tag Bulk Import PRD Revised In Place",
        )

        payload = dispatch_tool_call(
            "validate_repository",
            {},
            paths=[str(fixture_root)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(payload["issue_count"], 1)
        self.assertEqual(payload["issues"][0]["code"], "immutable_artifact_mutation")
        self.assertEqual(payload["issues"][0]["object_id"], "PRD-2026-001")

    def test_dispatch_check_feature_readiness_returns_golden_path_payload_for_example(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        summary_payload = dispatch_tool_call(
            "check_feature_readiness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertTrue(summary_payload["ready"])
        self.assertEqual(summary_payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary_payload["artifact_ids"], [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
            "TEST-2026-001",
        ])
        self.assertEqual(summary_payload["blocking_validation_issue_count"], 0)
        self.assertEqual(summary_payload["open_question_count"], 0)
        self.assertEqual(summary_payload["blocker_count"], 0)
        self.assertEqual(summary_payload["validation_issues"], [])
        self.assertEqual(summary_payload["blockers"], [])
        self.assertEqual(
            [item["artifact_type"] for item in summary_payload["artifact_gap_map"]],
            [
                "brief",
                "prd_story_pack",
                "solution_design",
                "execution_plan",
                "test_acceptance",
                "release_review",
            ],
        )
        self.assertTrue(all(not item["blocking_gaps"] for item in summary_payload["artifact_gap_map"]))
        self.assertTrue(all(not item["attention_items"] for item in summary_payload["artifact_gap_map"]))
        json.dumps(summary_payload, sort_keys=True)

    def test_dispatch_check_feature_readiness_for_versioned_example_uses_baseline_artifacts_only(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        summary_payload = dispatch_tool_call(
            "check_feature_readiness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(VERSIONED_EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(summary_payload["artifact_ids"], [
            "BRIEF-2026-002",
            "DESIGN-2026-002",
            "EXEC-2026-002",
            "PRD-2026-002",
            "RELEASE-2026-002",
            "TEST-2026-002",
        ])
        self.assertEqual(summary_payload["baseline_artifact_ids"], summary_payload["artifact_ids"])
        self.assertEqual(summary_payload["ambiguous_artifact_families"], [])
        self.assertTrue(summary_payload["ready"])
        self.assertEqual(
            sorted(
                artifact_id
                for item in summary_payload["artifact_gap_map"]
                for artifact_id in item["artifact_ids"]
            ),
            summary_payload["artifact_ids"],
        )
        self.assertNotIn(
            "PRD-2026-001",
            [artifact_id for item in summary_payload["artifact_gap_map"] for artifact_id in item["artifact_ids"]],
        )
        json.dumps(summary_payload, sort_keys=True)

    def test_dispatch_check_feature_readiness_blocked_flow_surfaces_artifact_gap_map(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        payload = dispatch_tool_call(
            "check_feature_readiness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(INVALID_ILLEGAL_STATUS_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        execution_entry = next(item for item in payload["artifact_gap_map"] if item["artifact_type"] == "execution_plan")

        self.assertFalse(payload["ready"])
        self.assertGreater(payload["blocker_count"], 0)
        self.assertTrue(
            any(
                gap["kind"] == "validation_issue" and gap["code"] == "invalid_status_transition"
                for gap in execution_entry["blocking_gaps"]
            )
        )
        json.dumps(payload, sort_keys=True)

    def test_dispatch_check_feature_readiness_git_backed_immutable_mutation_surfaces_artifact_gap_map(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        replace_in_file(
            fixture_root / "02_prd.md",
            "title: User Tag Bulk Import PRD",
            "title: User Tag Bulk Import PRD Revised In Place",
        )

        payload = dispatch_tool_call(
            "check_feature_readiness",
            {"feature_key": "user-tag-bulk-import"},
            paths=[str(fixture_root)],
            schema_path=str(SCHEMA_PATH),
        )

        prd_entry = next(item for item in payload["artifact_gap_map"] if item["artifact_type"] == "prd_story_pack")

        self.assertFalse(payload["ready"])
        self.assertTrue(
            any(
                gap["kind"] == "validation_issue" and gap["code"] == "immutable_artifact_mutation"
                for gap in prd_entry["blocking_gaps"]
            )
        )
        json.dumps(payload, sort_keys=True)

    def test_dispatch_check_release_readiness_returns_golden_path_payload_for_example(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        summary_payload = dispatch_tool_call(
            "check_release_readiness",
            {"release_target": "2026.04"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(summary_payload["release_target"], "2026.04")
        self.assertEqual(summary_payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary_payload["release_artifact_ids"], ["RELEASE-2026-001"])
        self.assertTrue(summary_payload["ready"])
        self.assertEqual(summary_payload["artifact_ids"], [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
            "TEST-2026-001",
        ])
        self.assertEqual(summary_payload["blocking_validation_issue_count"], 0)
        self.assertEqual(summary_payload["open_question_count"], 0)
        self.assertEqual(summary_payload["blocker_count"], 0)
        self.assertEqual(summary_payload["validation_issues"], [])
        self.assertEqual(summary_payload["blockers"], [])
        self.assertTrue(all(not item["missing_ids"] for item in summary_payload["coverage"]))
        json.dumps(summary_payload, sort_keys=True)

    def test_dispatch_check_release_readiness_for_versioned_example_uses_baseline_artifacts_only(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        summary_payload = dispatch_tool_call(
            "check_release_readiness",
            {"release_target": "2026.04"},
            paths=[str(VERSIONED_EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(summary_payload["artifact_ids"], [
            "BRIEF-2026-002",
            "DESIGN-2026-002",
            "EXEC-2026-002",
            "PRD-2026-002",
            "RELEASE-2026-002",
            "TEST-2026-002",
        ])
        self.assertEqual(summary_payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(summary_payload["baseline_artifact_ids"], summary_payload["artifact_ids"])
        self.assertEqual(summary_payload["release_artifact_ids"], ["RELEASE-2026-002"])
        self.assertEqual(summary_payload["ambiguous_artifact_families"], [])
        self.assertTrue(summary_payload["ready"])
        json.dumps(summary_payload, sort_keys=True)

    def test_dispatch_check_release_readiness_blocked_flow_surfaces_triage_counts(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        payload = dispatch_tool_call(
            "check_release_readiness",
            {"release_target": "2026.04"},
            paths=[str(INVALID_ILLEGAL_STATUS_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(payload["feature_key"], "user-tag-bulk-import")
        self.assertFalse(payload["ready"])
        self.assertGreater(payload["blocker_count"], 0)
        self.assertGreater(payload["blocking_validation_issue_count"], 0)
        self.assertGreaterEqual(payload["open_question_count"], 0)
        self.assertTrue(any(item["kind"] == "validation_issue" for item in payload["blockers"]))
        json.dumps(payload, sort_keys=True)

    def test_dispatch_analyze_change_impact_for_trace_unit_exposes_downstream_first_shape(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        impact_payload = dispatch_tool_call(
            "analyze_change_impact",
            {"object_id": "DEC-001"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(impact_payload["object_id"], "DEC-001")
        self.assertEqual(impact_payload["object_kind"], "trace_unit")
        self.assertEqual(impact_payload["owning_artifact_id"], "DESIGN-2026-001")
        self.assertEqual(impact_payload["trace_unit_ids"], ["DEC-001"])
        self.assertEqual(impact_payload["direct_downstream_trace_unit_ids"], ["TASK-001"])
        self.assertEqual(impact_payload["downstream_trace_unit_ids"], ["REL-001", "REV-001", "TASK-001"])
        self.assertEqual(impact_payload["downstream_artifact_ids"], ["EXEC-2026-001", "RELEASE-2026-001"])
        self.assertEqual(impact_payload["direct_upstream_trace_unit_ids"], ["NFR-001", "REQ-001"])
        self.assertEqual(impact_payload["upstream_trace_unit_ids"], ["GOAL-001", "NFR-001", "REQ-001"])
        self.assertEqual(impact_payload["upstream_artifact_ids"], ["BRIEF-2026-001", "PRD-2026-001"])
        self.assertEqual([edge["edge_id"] for edge in impact_payload["related_edges"]], ["EDGE-0003", "EDGE-0004", "EDGE-0005"])
        json.dumps(impact_payload, sort_keys=True)

    def test_dispatch_analyze_change_impact_for_artifact_exposes_seed_direct_and_transitive_context(self):
        _, dispatch_tool_call, _ = self.import_runtime()

        impact_payload = dispatch_tool_call(
            "analyze_change_impact",
            {"object_id": "DESIGN-2026-001"},
            paths=[str(EXAMPLE_DIR)],
            schema_path=str(SCHEMA_PATH),
        )

        self.assertEqual(impact_payload["object_id"], "DESIGN-2026-001")
        self.assertEqual(impact_payload["object_kind"], "artifact")
        self.assertEqual(impact_payload["owning_artifact_id"], "DESIGN-2026-001")
        self.assertEqual(impact_payload["trace_unit_ids"], ["DEC-001", "RISK-001"])
        self.assertEqual(impact_payload["direct_downstream_trace_unit_ids"], ["TASK-001"])
        self.assertEqual(impact_payload["downstream_trace_unit_ids"], ["REL-001", "REV-001", "TASK-001"])
        self.assertEqual(impact_payload["downstream_artifact_ids"], ["EXEC-2026-001", "RELEASE-2026-001"])
        self.assertEqual(impact_payload["direct_upstream_trace_unit_ids"], ["NFR-001", "REQ-001"])
        self.assertEqual(impact_payload["upstream_trace_unit_ids"], ["GOAL-001", "NFR-001", "REQ-001"])
        self.assertEqual(impact_payload["upstream_artifact_ids"], ["BRIEF-2026-001", "PRD-2026-001"])
        self.assertEqual([edge["edge_id"] for edge in impact_payload["related_edges"]], ["EDGE-0003", "EDGE-0004", "EDGE-0005"])
        json.dumps(impact_payload, sort_keys=True)

    def test_build_mcp_server_returns_fastmcp_instance(self):
        build_mcp_server, _, _ = self.import_runtime()

        server = build_mcp_server(paths=[str(EXAMPLE_DIR)], schema_path=str(SCHEMA_PATH))

        self.assertEqual(type(server).__name__, "FastMCP")


if __name__ == "__main__":
    unittest.main()
