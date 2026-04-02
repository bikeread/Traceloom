import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.git_fixture_helpers import init_git_example_repo, replace_in_file


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class CliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "traceloom", *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_validate_command_accepts_example_flow(self):
        result = self.run_cli("validate", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("Validation passed", result.stdout)

    def test_workspace_create_command_defaults_to_minimal_template(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["name"], "billing-intake")
            self.assertEqual(payload["source_kind"], "minimal_requirement_template")
            self.assertTrue((Path(payload["active_repository_path"]) / "01_brief.md").is_file())
            self.assertFalse((Path(payload["active_repository_path"]) / "02_prd.md").exists())

    def test_workspace_create_command_accepts_full_template_selector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(
                "workspace",
                "create",
                "billing-intake",
                "--root",
                temp_dir,
                "--template",
                "full",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["source_kind"], "starter_template")
            self.assertTrue((Path(payload["active_repository_path"]) / "02_prd.md").is_file())

    def test_workspace_list_command_outputs_created_workspace_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            create_result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr or create_result.stdout)

            result = self.run_cli("workspace", "list", "--root", temp_dir)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual([item["name"] for item in payload], ["billing-intake"])

    def test_workspace_show_command_outputs_structured_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            create_result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr or create_result.stdout)

            result = self.run_cli("workspace", "show", "billing-intake", "--root", temp_dir)

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["name"], "billing-intake")
            self.assertEqual(payload["source_kind"], "minimal_requirement_template")

    def test_workspace_create_command_rejects_duplicate_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)
            self.assertEqual(first.returncode, 0, msg=first.stderr or first.stdout)

            result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("workspace 'billing-intake' already exists", result.stderr or result.stdout)

    def test_workspace_create_command_rejects_invalid_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli("workspace", "create", "../escape", "--root", temp_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid workspace name", result.stderr or result.stdout)

    def test_bootstrap_prepare_command_outputs_seed_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_file = Path(temp_dir) / "bootstrap-request.json"
            request_file.write_text(
                json.dumps(
                    {
                        "intent": {
                            "current_requirement_statement": "Shape the PRD seed for the billing intake slice.",
                            "target_user": "operations",
                            "target_outcome": "prd seed",
                        },
                        "conversation": "The billing intake slice is clear enough to shape a PRD seed and continue PM-led refinement.",
                        "primary_source": {
                            "title": "Billing intake note",
                            "summary": "Constrains the current billing intake requirement slice.",
                        },
                        "supporting_sources": [
                            {
                                "title": "Billing intake ticket",
                                "summary": "Adds supporting billing intake requirement context.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli("bootstrap", "prepare", "--request-file", str(request_file))

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["progression_level"], "brief_plus_prd_seed")
            self.assertIn("brief_draft", payload)
            self.assertIn("prd_seed_draft", payload)
            self.assertEqual(
                sorted(payload["evidence_map"].keys()),
                ["derived_inferences", "evidence_backed_facts", "missing_evidence"],
            )
            self.assertIn("follow_up_questions", payload)
            self.assertEqual(payload["eligible_next_artifact_types"], ["brief", "prd_story_pack"])

    def test_bootstrap_apply_command_materializes_seed_into_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            create_result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr or create_result.stdout)

            seed_file = Path(temp_dir) / "bootstrap-seed.json"
            seed_file.write_text(
                json.dumps(
                    {
                        "progression_level": "brief_plus_prd_seed",
                        "brief_draft": {
                            "artifact_id": "BRIEF-2026-900",
                            "title": "Retry-Safe Bulk Import Brief",
                            "summary": "Clarify operator-safe retry behavior.",
                            "body_markdown": "## Background\n\nOperators need safe retries.\n",
                            "scope": {
                                "product_area": "growth",
                                "feature_key": "billing-intake",
                                "in_scope": ["retry-safe import guidance"],
                            },
                        },
                        "prd_seed_draft": {
                            "artifact_id": "PRD-2026-900",
                            "title": "Retry-Safe Bulk Import PRD",
                            "summary": "Define retry-safe import requirements.",
                            "body_markdown": "## Requirements\n\n- Prevent duplicate writes.\n",
                            "scope": {
                                "product_area": "growth",
                                "feature_key": "billing-intake",
                                "in_scope": ["retry-safe import guidance"],
                            },
                        },
                        "evidence_map": {
                            "evidence_backed_facts": ["Operators need safe retries."],
                            "derived_inferences": ["A PRD seed is justified."],
                            "missing_evidence": ["Need confirmation on rollback UX."],
                        },
                        "scope_assumptions": ["No new admin UI in phase 1."],
                        "open_questions": ["Should retries be idempotent across file re-uploads?"],
                        "next_handoff_recommendation": {
                            "capability": "pm",
                            "target_stage": "prd",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "bootstrap",
                "apply",
                "--seed-file",
                str(seed_file),
                "--workspace",
                "billing-intake",
                "--root",
                temp_dir,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["workspace_name"], "billing-intake")
            artifact = json.loads(
                self.run_cli(
                    "artifact",
                    "BRIEF-2026-900",
                    "--workspace",
                    "billing-intake",
                    "--root",
                    temp_dir,
                    "--view",
                    "full",
                ).stdout
            )
            self.assertEqual(artifact["header"]["title"], "Retry-Safe Bulk Import Brief")
            self.assertIn("Operators need safe retries.", artifact["body"])

    def test_navigate_feature_command_accepts_workspace_selector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            create_result = self.run_cli("workspace", "create", "billing-intake", "--root", temp_dir)
            self.assertEqual(create_result.returncode, 0, msg=create_result.stderr or create_result.stdout)

            seed_file = Path(temp_dir) / "bootstrap-seed.json"
            seed_file.write_text(
                json.dumps(
                    {
                        "progression_level": "brief_only",
                        "brief_draft": {
                            "artifact_id": "BRIEF-2026-901",
                            "title": "Billing Intake Brief",
                            "summary": "Seed the billing intake requirement.",
                            "body_markdown": "## Background\n\nSeed content.\n",
                            "scope": {
                                "product_area": "growth",
                                "feature_key": "billing-intake",
                                "in_scope": ["billing intake workflow"],
                            },
                        },
                        "evidence_map": {
                            "evidence_backed_facts": ["Seed content."],
                            "derived_inferences": [],
                            "missing_evidence": ["Need user journey details."],
                        },
                        "scope_assumptions": ["Internal users only."],
                        "open_questions": ["What is the initial import volume target?"],
                        "next_handoff_recommendation": {
                            "capability": "pm",
                            "target_stage": "brief",
                        },
                    }
                ),
                encoding="utf-8",
            )
            apply_result = self.run_cli(
                "bootstrap",
                "apply",
                "--seed-file",
                str(seed_file),
                "--workspace",
                "billing-intake",
                "--root",
                temp_dir,
            )
            self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr or apply_result.stdout)

            result = self.run_cli(
                "navigate-feature",
                "billing-intake",
                "--workspace",
                "billing-intake",
                "--root",
                temp_dir,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["feature_key"], "billing-intake")

    def test_validate_command_reports_git_backed_immutable_mutation(self):
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        replace_in_file(
            fixture_root / "02_prd.md",
            "title: User Tag Bulk Import PRD",
            "title: User Tag Bulk Import PRD Revised In Place",
        )

        result = self.run_cli("validate", str(fixture_root))

        self.assertEqual(result.returncode, 1, msg=result.stderr or result.stdout)
        self.assertIn("ERROR immutable_artifact_mutation", result.stdout)
        self.assertIn("PRD-2026-001", result.stdout)

    def test_trace_command_prints_related_units(self):
        result = self.run_cli("trace", "REQ-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("REQ-001", result.stdout)
        self.assertIn("GOAL-001", result.stdout)
        self.assertIn("AC-001", result.stdout)
        self.assertIn("DEC-001", result.stdout)

    def test_coverage_command_reports_counts(self):
        result = self.run_cli("coverage", "AC", "TC", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("covered: 1", result.stdout)
        self.assertIn("missing: 0", result.stdout)

    def test_artifact_command_outputs_json(self):
        result = self.run_cli("artifact", "PRD-2026-001", "--paths", str(EXAMPLE_DIR), "--view", "header")

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["artifact_id"], "PRD-2026-001")
        self.assertEqual(payload["header"]["status"], "done")

    def test_unit_command_outputs_json(self):
        result = self.run_cli("unit", "DEC-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(payload["unit"]["id"], "DEC-001")

    def test_related_command_outputs_filtered_relations(self):
        result = self.run_cli(
            "related",
            "REQ-001",
            "--paths",
            str(EXAMPLE_DIR),
            "--direction",
            "downstream",
            "--relation-type",
            "refines",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual([item["related_id"] for item in payload], ["AC-001"])

    def test_trace_upstream_and_downstream_commands_output_json(self):
        upstream = self.run_cli("trace-upstream", "REV-001", "--paths", str(EXAMPLE_DIR))
        downstream = self.run_cli("trace-downstream", "GOAL-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(upstream.returncode, 0, msg=upstream.stderr or upstream.stdout)
        self.assertEqual(downstream.returncode, 0, msg=downstream.stderr or downstream.stdout)
        upstream_payload = json.loads(upstream.stdout)
        downstream_payload = json.loads(downstream.stdout)
        self.assertIn("GOAL-001", upstream_payload)
        self.assertIn("REV-001", downstream_payload)

    def test_history_command_outputs_status_history(self):
        result = self.run_cli("history", "PRD-2026-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[0]["to_status"], "approved")

    def test_questions_command_outputs_json_list(self):
        result = self.run_cli("questions", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, [])

    def test_versions_command_outputs_family_versions(self):
        result = self.run_cli("versions", "PRD-2026-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload[0]["artifact_id"], "PRD-2026-001")
        self.assertEqual(payload[0]["version"], "v0.1")

    def test_diff_versions_command_outputs_structured_diff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_root = Path(temp_dir) / "query-fixture"
            shutil.copytree(EXAMPLE_DIR, fixture_root)

            source = (fixture_root / "02_prd.md").read_text(encoding="utf-8")
            successor = source.replace(
                "artifact_id: PRD-2026-001",
                "artifact_id: PRD-2026-002",
            ).replace(
                "version: v0.1",
                "version: v0.2",
            ).replace(
                "summary: Define the CSV import workflow, validation rules, and acceptance criteria for batch user tag assignment.",
                "summary: Define the CSV import workflow, retry-safe commit behavior, and acceptance criteria for batch user tag assignment.",
            )
            (fixture_root / "02_prd_v0_2.md").write_text(successor, encoding="utf-8")

            result = self.run_cli(
                "diff-versions",
                "PRD-2026-001",
                "v0.1",
                "v0.2",
                "--paths",
                str(fixture_root),
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["from_artifact_id"], "PRD-2026-001")
        self.assertEqual(payload["to_artifact_id"], "PRD-2026-002")
        self.assertIn("summary", payload["changed_header_fields"])

    def test_workflow_command_outputs_structured_gate_result(self):
        result = self.run_cli("workflow", "PRD-2026-001", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["artifact_id"], "PRD-2026-001")
        self.assertEqual(payload["gate_id"], "prd_gate")
        self.assertEqual(payload["current_outcome"], "approved")
        self.assertEqual(payload["missing_approval_capabilities"], [])
        self.assertTrue(payload["controlled_transition_allowed"])

    def test_workflow_command_accepts_explicit_schema_path(self):
        result = self.run_cli(
            "workflow",
            "RELEASE-2026-001",
            "--paths",
            str(EXAMPLE_DIR),
            "--schema",
            str(SCHEMA_PATH),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_id"], "release_review_gate")

    def test_navigate_feature_command_outputs_delivery_slice_payload(self):
        result = self.run_cli("navigate-feature", "user-tag-bulk-import", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(payload["slice_stage"], "design_handoff_ready")
        self.assertEqual(payload["current_focus"]["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(payload["next_recommended_capability"], "tech_lead")
        self.assertEqual(payload["handoff_readiness"]["ready"], True)

    def test_navigate_feature_command_accepts_explicit_schema_path(self):
        result = self.run_cli(
            "navigate-feature",
            "user-tag-bulk-import",
            "--paths",
            str(VERSIONED_EXAMPLE_DIR),
            "--schema",
            str(SCHEMA_PATH),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["slice_stage"], "brief_in_progress")
        self.assertEqual(payload["artifacts"]["brief"]["artifact_id"], "BRIEF-2026-002")

    def test_design_check_command_outputs_structured_payload(self):
        result = self.run_cli("design-check", "user-tag-bulk-import", "--paths", str(EXAMPLE_DIR))

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["feature_key"], "user-tag-bulk-import")
        self.assertEqual(payload["design_artifact_id"], "DESIGN-2026-001")
        self.assertEqual(payload["ready"], True)

    def test_prepare_guided_action_command_outputs_package_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_file = Path(temp_dir) / "guided-action-request.json"
            request_file.write_text(
                json.dumps(
                    {
                        "action_type": "revise_artifact_draft",
                        "content_payload": {
                            "title": "Retry-Safe Bulk Import Brief",
                            "summary": "Clarify the revised problem framing.",
                            "body_markdown": "# Goal\n\nClarify retry-safe operator guidance.\n",
                        },
                        "governance_payload": {
                            "actor_id": "user:li.pm",
                            "role": "pm",
                            "capability": "artifact_authoring",
                            "decision_authority": "brief_owner",
                            "changed_at": "2026-03-25T18:00:00+08:00",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "prepare-guided-action",
                "user-tag-bulk-import",
                "--paths",
                str(VERSIONED_EXAMPLE_DIR),
                "--request-file",
                str(request_file),
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["action"]["action_type"], "revise_artifact_draft")
        self.assertEqual(payload["target"]["artifact_id"], "BRIEF-2026-002")
        self.assertEqual(payload["recommended_by"]["surface"], "get_delivery_slice_navigation")

    def test_execute_guided_action_command_outputs_acceptance_json(self):
        temp_dir, fixture_root = init_git_example_repo(VERSIONED_EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        request_file = fixture_root / "guided-action-request.json"
        request_file.write_text(
            json.dumps(
                {
                    "action_type": "revise_artifact_draft",
                    "content_payload": {
                        "title": "Retry-Safe Bulk Import Brief v0.2",
                        "summary": "CLI guided action summary.",
                        "body_markdown": (
                            (fixture_root / "12_brief_v0_2.md")
                            .read_text(encoding="utf-8")
                            .split("---\n", 2)[2]
                            .lstrip("\n")
                            .replace(
                                "retry-safe operator behavior.",
                                "retry-safe operator behavior and support escalation steps.",
                            )
                        ),
                    },
                    "governance_payload": {
                        "actor_id": "user:li.pm",
                        "role": "pm",
                        "capability": "artifact_authoring",
                        "decision_authority": "brief_owner",
                        "changed_at": "2026-03-25T18:05:00+08:00",
                    },
                }
            ),
            encoding="utf-8",
        )

        prepare_result = self.run_cli(
            "prepare-guided-action",
            "user-tag-bulk-import",
            "--paths",
            str(fixture_root),
            "--request-file",
            str(request_file),
        )
        self.assertEqual(prepare_result.returncode, 0, msg=prepare_result.stderr or prepare_result.stdout)

        package_file = fixture_root / "guided-action-package.json"
        package_file.write_text(prepare_result.stdout, encoding="utf-8")

        result = self.run_cli(
            "execute-guided-action",
            "--paths",
            str(fixture_root),
            "--package-file",
            str(package_file),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["executed_action"], "revise_artifact_draft")
        artifact = json.loads(
            self.run_cli("artifact", "BRIEF-2026-002", "--paths", str(fixture_root), "--view", "full").stdout
        )
        self.assertEqual(artifact["header"]["summary"], "CLI guided action summary.")
        self.assertIn("support escalation steps", artifact["body"])

    def test_prepare_guided_action_command_accepts_workspace_selector_for_validation_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_file = Path(temp_dir) / "bootstrap-request.json"
            request_file.write_text(
                json.dumps(
                    {
                        "intent": {
                            "current_requirement_statement": "Shape the PRD seed for the onboarding slice.",
                            "target_user": "operations",
                            "target_outcome": "prd seed",
                        },
                        "conversation": "The scope is clear enough to shape a PRD seed and continue PM-led refinement.",
                        "primary_source": {
                            "title": "Current onboarding notes",
                            "summary": "A small source that directly constrains the requirement slice.",
                        },
                    }
                ),
                encoding="utf-8",
            )

            self.run_cli("workspace", "create", "demo-slice", "--root", temp_dir)
            prepare_seed = self.run_cli("bootstrap", "prepare", "--request-file", str(request_file))
            self.assertEqual(prepare_seed.returncode, 0, msg=prepare_seed.stderr or prepare_seed.stdout)

            seed_file = Path(temp_dir) / "bootstrap-seed.json"
            seed_file.write_text(prepare_seed.stdout, encoding="utf-8")
            apply_result = self.run_cli(
                "bootstrap",
                "apply",
                "--seed-file",
                str(seed_file),
                "--workspace",
                "demo-slice",
                "--root",
                temp_dir,
            )
            self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr or apply_result.stdout)

            guided_request = Path(temp_dir) / "guided-validation-request.json"
            guided_request.write_text(
                json.dumps(
                    {
                        "action_type": "record_validation_result",
                        "validation_payload": {
                            "validator_name": "qa.smoke",
                            "result": "pass",
                            "recorded_at": "2026-03-28T11:10:00+08:00",
                            "note": "Workspace validation remained green.",
                        },
                        "governance_payload": {
                            "actor_id": "user:qin.qa",
                            "role": "qa",
                            "capability": "qa",
                            "decision_authority": "qa_owner",
                            "changed_at": "2026-03-28T11:10:00+08:00",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(
                "prepare-guided-action",
                "demo-slice",
                "--workspace",
                "demo-slice",
                "--root",
                temp_dir,
                "--request-file",
                str(guided_request),
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["action"]["action_type"], "record_validation_result")
        self.assertEqual(payload["target"]["artifact_id"], "BRIEF-BOOTSTRAP-DEMO_SLICE")

    def test_execute_guided_action_command_accepts_workspace_selector_for_validation_action(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            request_file = Path(temp_dir) / "bootstrap-request.json"
            request_file.write_text(
                json.dumps(
                    {
                        "intent": {
                            "current_requirement_statement": "Shape the PRD seed for the onboarding slice.",
                            "target_user": "operations",
                            "target_outcome": "prd seed",
                        },
                        "conversation": "The scope is clear enough to shape a PRD seed and continue PM-led refinement.",
                        "primary_source": {
                            "title": "Current onboarding notes",
                            "summary": "A small source that directly constrains the requirement slice.",
                        },
                    }
                ),
                encoding="utf-8",
            )

            self.run_cli("workspace", "create", "demo-slice", "--root", temp_dir)
            prepare_seed = self.run_cli("bootstrap", "prepare", "--request-file", str(request_file))
            self.assertEqual(prepare_seed.returncode, 0, msg=prepare_seed.stderr or prepare_seed.stdout)

            seed_file = Path(temp_dir) / "bootstrap-seed.json"
            seed_file.write_text(prepare_seed.stdout, encoding="utf-8")
            apply_result = self.run_cli(
                "bootstrap",
                "apply",
                "--seed-file",
                str(seed_file),
                "--workspace",
                "demo-slice",
                "--root",
                temp_dir,
            )
            self.assertEqual(apply_result.returncode, 0, msg=apply_result.stderr or apply_result.stdout)

            guided_request = Path(temp_dir) / "guided-validation-request.json"
            guided_request.write_text(
                json.dumps(
                    {
                        "action_type": "record_validation_result",
                        "validation_payload": {
                            "validator_name": "qa.smoke",
                            "result": "pass",
                            "recorded_at": "2026-03-28T11:15:00+08:00",
                            "note": "Workspace validation remained green.",
                        },
                        "governance_payload": {
                            "actor_id": "user:qin.qa",
                            "role": "qa",
                            "capability": "qa",
                            "decision_authority": "qa_owner",
                            "changed_at": "2026-03-28T11:15:00+08:00",
                        },
                    }
                ),
                encoding="utf-8",
            )

            prepare_result = self.run_cli(
                "prepare-guided-action",
                "demo-slice",
                "--workspace",
                "demo-slice",
                "--root",
                temp_dir,
                "--request-file",
                str(guided_request),
            )
            self.assertEqual(prepare_result.returncode, 0, msg=prepare_result.stderr or prepare_result.stdout)

            package_file = Path(temp_dir) / "guided-validation-package.json"
            package_file.write_text(prepare_result.stdout, encoding="utf-8")

            result = self.run_cli(
                "execute-guided-action",
                "--workspace",
                "demo-slice",
                "--root",
                temp_dir,
                "--package-file",
                str(package_file),
            )

            artifact = json.loads(
                self.run_cli(
                    "artifact",
                    "BRIEF-BOOTSTRAP-DEMO_SLICE",
                    "--workspace",
                    "demo-slice",
                    "--root",
                    temp_dir,
                    "--view",
                    "header",
                ).stdout
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["accepted"])
        self.assertEqual(payload["executed_action"], "record_validation_result")
        self.assertEqual(artifact["header"]["validation_records"][-1]["validator_name"], "qa.smoke")

    def test_execute_guided_action_command_outputs_stale_rejection_json(self):
        from traceloom.artifact_io import write_artifact_header
        from traceloom.guided_actions import prepare_guided_action_package
        from traceloom.parser import parse_artifact
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        (fixture_root / "02_prd.md").unlink()
        artifact = parse_artifact(fixture_root / "01_brief.md")
        header = dict(artifact.header)
        header["status"] = "in_review"
        header["updated_at"] = "2026-03-25T18:10:00+08:00"
        header["status_history"] = []
        header["downstream_refs"] = []
        write_artifact_header(fixture_root / "01_brief.md", header)

        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "promote_artifact_status",
                "target_status": "approved",
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_governance",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T18:15:00+08:00",
                },
            },
        )

        artifact = parse_artifact(fixture_root / "01_brief.md")
        header = dict(artifact.header)
        header["status"] = "draft"
        header["updated_at"] = "2026-03-25T18:16:00+08:00"
        header["review_records"] = []
        header["status_history"] = []
        header["downstream_refs"] = []
        write_artifact_header(fixture_root / "01_brief.md", header)

        package_file = fixture_root / "stale-guided-action-package.json"
        package_file.write_text(json.dumps(package), encoding="utf-8")

        result = self.run_cli(
            "execute-guided-action",
            "--paths",
            str(fixture_root),
            "--package-file",
            str(package_file),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["accepted"])
        self.assertEqual(payload["rejection_code"], "stale_navigation_context")
        self.assertEqual(
            payload["current_state"],
            {
                "slice_stage": "brief_in_progress",
                "current_focus_artifact_id": "BRIEF-2026-001",
            },
        )

    def test_mcp_command_print_tools_outputs_registered_names(self):
        result = self.run_cli("mcp", "--paths", str(EXAMPLE_DIR), "--print-tools")

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("validate_repository", result.stdout)
        self.assertIn("get_artifact", result.stdout)
        self.assertIn("check_feature_readiness", result.stdout)
        self.assertNotIn("create_artifact_draft", result.stdout)
        self.assertNotIn("revise_artifact_draft", result.stdout)
        self.assertNotIn("supersede_artifact_version", result.stdout)
        self.assertNotIn("prepare_guided_action_package", result.stdout)
        self.assertNotIn("execute_guided_action_package", result.stdout)

    def test_mcp_command_print_tools_accepts_demo_flag(self):
        result = self.run_cli("mcp", "--demo", "--print-tools")

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        self.assertIn("validate_repository", result.stdout)
        self.assertIn("get_delivery_slice_navigation", result.stdout)
        self.assertNotIn("execute_guided_action_package", result.stdout)

    def test_mcp_command_rejects_mixing_demo_and_paths(self):
        result = self.run_cli("mcp", "--demo", "--paths", str(EXAMPLE_DIR), "--print-tools")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--demo cannot be used together with --paths", result.stderr or result.stdout)

    def test_mcp_command_accepts_explicit_schema_path(self):
        result = self.run_cli(
            "mcp",
            "--paths",
            str(EXAMPLE_DIR),
            "--schema",
            str(SCHEMA_PATH),
            "--print-tools",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        payload = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertIn("check_release_readiness", payload)

    def test_record_review_decision_command_updates_artifact(self):
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = self.run_cli(
            "record-review-decision",
            "DESIGN-2026-001",
            "--paths",
            str(fixture_root),
            "--actor-id",
            "user:zhou.tl",
            "--role",
            "tech_lead",
            "--capability",
            "design_review",
            "--decision-authority",
            "tech_lead_approval",
            "--decision",
            "approve",
            "--recorded-at",
            "2026-03-24T15:00:00+08:00",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "DESIGN-2026-001", "--paths", str(fixture_root), "--view", "header").stdout
        )
        self.assertEqual(artifact["header"]["review_records"][-1]["decision"], "approve")
        self.assertEqual(artifact["header"]["review_records"][-1]["reviewer"]["capability"], "design_review")
        self.assertEqual(artifact["header"]["review_records"][-1]["reviewer"]["decision_authority"], "tech_lead_approval")

    def test_record_validation_result_command_updates_immutable_artifact(self):
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = self.run_cli(
            "record-validation-result",
            "TEST-2026-001",
            "--paths",
            str(fixture_root),
            "--validator-name",
            "qa.smoke",
            "--result",
            "pass",
            "--recorded-at",
            "2026-03-24T16:00:00+08:00",
            "--note",
            "Post-release smoke rerun remains green.",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "TEST-2026-001", "--paths", str(fixture_root), "--view", "header").stdout
        )
        self.assertEqual(artifact["header"]["validation_records"][-1]["validator_name"], "qa.smoke")

    def test_create_artifact_draft_command_writes_new_file(self):
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = self.run_cli(
            "create-artifact-draft",
            "--paths",
            str(fixture_root),
            "--path",
            "12_prd_v0_2.md",
            "--artifact-id",
            "PRD-2026-002",
            "--artifact-type",
            "prd_story_pack",
            "--title",
            "Retry-Safe Bulk Import PRD",
            "--summary",
            "Revise the requirement contract for retry-safe commit semantics.",
            "--version",
            "v0.2",
            "--actor-id",
            "user:li.pm",
            "--role",
            "pm",
            "--capability",
            "artifact_authoring",
            "--decision-authority",
            "prd_owner",
            "--product-area",
            "growth",
            "--feature-key",
            "user-tag-bulk-import",
            "--in-scope",
            "retry-safe commit",
            "--created-at",
            "2026-03-25T11:30:00+08:00",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "PRD-2026-002", "--paths", str(fixture_root), "--view", "header").stdout
        )
        self.assertEqual(artifact["header"]["status"], "draft")
        self.assertEqual(artifact["header"]["owner"]["capability"], "artifact_authoring")
        self.assertEqual(artifact["header"]["owner"]["decision_authority"], "prd_owner")
        self.assertTrue((fixture_root / "12_prd_v0_2.md").exists())

    def test_revise_artifact_draft_command_updates_body_and_summary(self):
        temp_dir, fixture_root = init_git_example_repo(VERSIONED_EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        body_path = fixture_root / "updated-prd-body.md"
        source_body = (fixture_root / "08_prd_v0_2.md").read_text(encoding="utf-8").split("---\n", 2)[2].lstrip("\n")
        body_path.write_text(
            source_body.replace(
                "reviews a preview, retries safely after transient failures, and then commits the import.",
                "reviews a preview, retries safely after transient failures, and only commits after operator acknowledgement.",
            ),
            encoding="utf-8",
        )

        result = self.run_cli(
            "revise-artifact-draft",
            "PRD-2026-002",
            "--paths",
            str(fixture_root),
            "--body-file",
            str(body_path),
            "--summary",
            "CLI revised summary.",
            "--updated-at",
            "2026-03-25T11:40:00+08:00",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "PRD-2026-002", "--paths", str(fixture_root), "--view", "full").stdout
        )
        self.assertEqual(artifact["header"]["summary"], "CLI revised summary.")
        self.assertIn("operator acknowledgement", artifact["body"])

    def test_supersede_artifact_version_command_updates_successor_relation_edges(self):
        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        create_result = self.run_cli(
            "create-artifact-draft",
            "--paths",
            str(fixture_root),
            "--path",
            "12_prd_v0_2.md",
            "--artifact-id",
            "PRD-2026-002",
            "--artifact-type",
            "prd_story_pack",
            "--title",
            "Retry-Safe Bulk Import PRD",
            "--summary",
            "Revise the requirement contract for retry-safe commit semantics.",
            "--version",
            "v0.2",
            "--actor-id",
            "user:li.pm",
            "--role",
            "pm",
            "--product-area",
            "growth",
            "--feature-key",
            "user-tag-bulk-import",
            "--in-scope",
            "retry-safe commit",
            "--created-at",
            "2026-03-25T11:45:00+08:00",
        )
        self.assertEqual(create_result.returncode, 0, msg=create_result.stderr or create_result.stdout)

        result = self.run_cli(
            "supersede-artifact-version",
            "PRD-2026-002",
            "PRD-2026-001",
            "--paths",
            str(fixture_root),
            "--edge-id",
            "EDGE-2003",
            "--actor-id",
            "user:li.pm",
            "--role",
            "pm",
            "--capability",
            "artifact_governance",
            "--decision-authority",
            "prd_owner",
            "--created-at",
            "2026-03-25T11:50:00+08:00",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "PRD-2026-002", "--paths", str(fixture_root), "--view", "full").stdout
        )
        self.assertEqual(artifact["relation_edges"][-1]["relation_type"], "supersedes")
        self.assertEqual(artifact["relation_edges"][-1]["created_by"]["capability"], "artifact_governance")
        self.assertEqual(artifact["relation_edges"][-1]["created_by"]["decision_authority"], "prd_owner")

    def test_promote_artifact_status_command_updates_status_and_history(self):
        from traceloom.artifact_io import write_artifact_header
        from traceloom.parser import parse_artifact

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "03_solution_design.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "approved"
        header["updated_at"] = "2026-03-24T15:30:00+08:00"
        header["status_history"] = [artifact.header["status_history"][0]]
        write_artifact_header(target, header)

        result = self.run_cli(
            "promote-artifact-status",
            "DESIGN-2026-001",
            "active",
            "--paths",
            str(fixture_root),
            "--actor-id",
            "user:zhou.tl",
            "--role",
            "tech_lead",
            "--capability",
            "artifact_governance",
            "--decision-authority",
            "design_activation",
            "--changed-at",
            "2026-03-24T16:00:00+08:00",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        artifact = json.loads(
            self.run_cli("artifact", "DESIGN-2026-001", "--paths", str(fixture_root), "--view", "header").stdout
        )
        self.assertEqual(artifact["header"]["status"], "active")
        self.assertEqual(artifact["header"]["status_history"][-1]["to_status"], "active")
        self.assertEqual(artifact["header"]["status_history"][-1]["changed_by"]["capability"], "artifact_governance")
        self.assertEqual(artifact["header"]["status_history"][-1]["changed_by"]["decision_authority"], "design_activation")


if __name__ == "__main__":
    unittest.main()
