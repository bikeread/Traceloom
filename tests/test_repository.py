from copy import deepcopy
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tests.git_fixture_helpers import init_git_example_repo


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class RepositoryTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.repository import load_repository
            from traceloom.validators import calculate_coverage, load_schema, validate_repository
        except ImportError as exc:
            self.fail(f"could not import repository or validators runtime: {exc}")
        return load_repository, load_schema, validate_repository, calculate_coverage

    def load_example_validation_context(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)
        repository = load_repository([EXAMPLE_DIR])
        return repository, schema, validate_repository

    def missing_traceability_messages(self, issues):
        return [issue.message for issue in issues if issue.code == "missing_traceability"]

    def governance_messages(self, issues):
        return [
            issue.message
            for issue in issues
            if issue.code in {
                "missing_required_review_record",
                "missing_status_history_transition",
                "invalid_status_transition",
                "status_history_sequence_mismatch",
                "status_history_current_status_mismatch",
                "missing_supersedes_link",
                "supersedes_family_mismatch",
                "supersedes_same_version",
                "immutable_artifact_mutation",
            }
        ]

    def add_artifact_version_clone(
        self,
        repository,
        source_artifact_id,
        *,
        new_artifact_id,
        version,
        status,
    ):
        source = repository.artifacts_by_id[source_artifact_id]
        header = deepcopy(source.header)
        header["artifact_id"] = new_artifact_id
        header["version"] = version
        header["status"] = status
        header["created_at"] = "2026-03-24T09:00:00+08:00"
        header["updated_at"] = "2026-03-24T09:00:00+08:00"
        header["review_records"] = []
        header["status_history"] = []
        header["change_summary"] = [
            f"{new_artifact_id} replaces {source_artifact_id} as the next draft version"
        ]
        repository.artifacts_by_id[new_artifact_id] = source.__class__(
            path=EXAMPLE_DIR / f"{new_artifact_id.lower()}.md",
            header=header,
            body=source.body,
            headings=list(source.headings),
            trace_units=deepcopy(source.trace_units),
            relation_edges=[],
        )

    def test_load_repository_indexes_example_artifacts_and_trace_units(self):
        load_repository, _, _, _ = self.import_runtime()

        repository = load_repository([EXAMPLE_DIR])

        self.assertEqual(sorted(repository.artifacts_by_id), [
            "BRIEF-2026-001",
            "DESIGN-2026-001",
            "EXEC-2026-001",
            "PRD-2026-001",
            "RELEASE-2026-001",
            "TEST-2026-001",
        ])
        self.assertIn("GOAL-001", repository.trace_units_by_id)
        self.assertIn("REV-001", repository.trace_units_by_id)
        self.assertIn("EDGE-0010", repository.relation_edges_by_id)

    def test_validate_repository_accepts_example_flow(self):
        load_repository, load_schema, validate_repository, calculate_coverage = self.import_runtime()

        schema = load_schema(SCHEMA_PATH)
        repository = load_repository([EXAMPLE_DIR])
        issues = validate_repository(repository, schema)
        coverage = calculate_coverage(repository, "REQ", "AC")

        self.assertEqual(issues, [])
        self.assertEqual(coverage["covered"], ["REQ-001"])
        self.assertEqual(coverage["missing"], [])

    def test_validate_repository_accepts_committed_versioned_example_flow(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()

        self.assertTrue(VERSIONED_EXAMPLE_DIR.is_dir())

        schema = load_schema(SCHEMA_PATH)
        repository = load_repository([VERSIONED_EXAMPLE_DIR])
        issues = validate_repository(repository, schema)

        self.assertEqual(issues, [])

    def test_validate_repository_accepts_validation_records_on_artifact_header(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["TEST-2026-001"]
        artifact.header["validation_records"] = [
            {
                "validator_name": "qa.smoke",
                "result": "pass",
                "recorded_at": "2026-03-24T10:00:00+08:00",
            }
        ]

        issues = validate_repository(repository, schema)

        self.assertFalse(any(issue.object_id == "TEST-2026-001" and "validation_records" in issue.message for issue in issues))

    def test_validate_repository_reports_malformed_validation_records(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["TEST-2026-001"]
        artifact.header["validation_records"] = [
            {
                "validator_name": ["qa.smoke"],
                "result": "pass",
                "recorded_at": "not-a-datetime",
            }
        ]

        issues = validate_repository(repository, schema)

        self.assertTrue(
            any(issue.object_id == "TEST-2026-001" and "validation_records[0]" in issue.message for issue in issues)
        )

    def test_validate_repository_accepts_actor_audit_metadata_in_governed_records(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["DESIGN-2026-001"]
        artifact.header["review_records"][0]["reviewer"]["capability"] = "design_review"
        artifact.header["review_records"][0]["reviewer"]["decision_authority"] = "required_reviewer_role"
        artifact.header["status_history"][0]["changed_by"]["capability"] = "technical_approval"
        artifact.header["status_history"][0]["changed_by"]["decision_authority"] = "owner_roles"

        issues = validate_repository(repository, schema)

        self.assertFalse(any(issue.object_id == "DESIGN-2026-001" and "capability" in issue.message for issue in issues))
        self.assertFalse(
            any(issue.object_id == "DESIGN-2026-001" and "decision_authority" in issue.message for issue in issues)
        )

    def test_validate_repository_reports_malformed_actor_audit_metadata(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["DESIGN-2026-001"]
        artifact.header["review_records"][0]["reviewer"]["capability"] = ["design_review"]
        artifact.header["review_records"][0]["reviewer"]["decision_authority"] = {"mode": "required_reviewer_role"}

        issues = validate_repository(repository, schema)

        self.assertTrue(
            any(issue.object_id == "DESIGN-2026-001" and "review_records[0].reviewer.capability" in issue.message for issue in issues)
        )
        self.assertTrue(
            any(
                issue.object_id == "DESIGN-2026-001"
                and "review_records[0].reviewer.decision_authority" in issue.message
                for issue in issues
            )
        )

    def test_validate_repository_allows_draft_artifact_without_required_trace_units(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["PRD-2026-001"]
        artifact.header["status"] = "draft"
        artifact.header["review_records"] = []
        artifact.header["status_history"] = []
        artifact.trace_units = []

        issues = validate_repository(repository, schema)

        self.assertFalse(
            any(issue.object_id == "PRD-2026-001" and issue.code == "missing_required_trace_units" for issue in issues)
        )

    def test_validate_repository_allows_missing_req_to_ac_for_draft_prd(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["PRD-2026-001"].header["status"] = "draft"
        repository.relation_edges_by_id.pop("EDGE-0002")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertFalse(any("REQ-001" in message and "AC" in message for message in messages))

    def test_validate_repository_reports_missing_req_to_ac_for_in_review_prd(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["PRD-2026-001"].header["status"] = "in_review"
        repository.relation_edges_by_id.pop("EDGE-0002")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertTrue(any("REQ-001" in message and "AC" in message for message in messages))

    def test_validate_repository_allows_missing_req_to_dec_for_draft_design(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["DESIGN-2026-001"].header["status"] = "draft"
        repository.relation_edges_by_id.pop("EDGE-0003")
        repository.relation_edges_by_id.pop("EDGE-0004")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertFalse(any("REQ-001" in message and "DEC" in message for message in messages))
        self.assertFalse(any("NFR-001" in message and "DEC" in message for message in messages))

    def test_validate_repository_reports_missing_req_to_dec_for_in_review_design(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["DESIGN-2026-001"].header["status"] = "in_review"
        repository.relation_edges_by_id.pop("EDGE-0003")
        repository.relation_edges_by_id.pop("EDGE-0004")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertTrue(any("REQ-001" in message and "DEC" in message for message in messages))
        self.assertTrue(any("NFR-001" in message and "DEC" in message for message in messages))

    def test_validate_repository_allows_missing_ac_to_tc_for_in_review_test_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["TEST-2026-001"].header["status"] = "in_review"
        repository.relation_edges_by_id.pop("EDGE-0006")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertFalse(any("AC-001" in message and "TC" in message for message in messages))

    def test_validate_repository_reports_missing_ac_to_tc_for_approved_test_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["TEST-2026-001"].header["status"] = "approved"
        repository.relation_edges_by_id.pop("EDGE-0006")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertTrue(any("AC-001" in message and "TC" in message for message in messages))

    def test_validate_repository_allows_missing_release_review_coverage_before_active(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["RELEASE-2026-001"].header["status"] = "approved"
        repository.relation_edges_by_id.pop("EDGE-0007")
        repository.relation_edges_by_id.pop("EDGE-0008")
        repository.relation_edges_by_id.pop("EDGE-0009")
        repository.relation_edges_by_id.pop("EDGE-0010")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertFalse(any("TASK-001" in message and "REL" in message for message in messages))
        self.assertFalse(any("REQ-001" in message and "REL" in message for message in messages))
        self.assertFalse(any("GOAL-001" in message and "REV" in message for message in messages))
        self.assertFalse(any("REL-001" in message and "REV" in message for message in messages))

    def test_validate_repository_reports_missing_release_review_coverage_when_active(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        repository.artifacts_by_id["RELEASE-2026-001"].header["status"] = "active"
        repository.relation_edges_by_id.pop("EDGE-0007")
        repository.relation_edges_by_id.pop("EDGE-0008")
        repository.relation_edges_by_id.pop("EDGE-0009")
        repository.relation_edges_by_id.pop("EDGE-0010")

        issues = validate_repository(repository, schema)

        messages = self.missing_traceability_messages(issues)
        self.assertTrue(any("TASK-001" in message and "REL" in message for message in messages))
        self.assertTrue(any("REQ-001" in message and "REL" in message for message in messages))
        self.assertTrue(any("GOAL-001" in message and "REV" in message for message in messages))
        self.assertTrue(any("REL-001" in message and "REV" in message for message in messages))

    def test_validate_repository_reports_missing_required_review_records_for_approved_prd(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["PRD-2026-001"]
        artifact.header["status"] = "approved"
        artifact.header["review_records"] = [
            {
                "reviewer": {
                    "actor_id": "user:zhou.tl",
                    "role": "tech_lead",
                },
                "decision": "approve",
                "recorded_at": "2026-03-23T15:00:00+08:00",
                "related_transition": "in_review->approved",
            }
        ]

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("PRD-2026-001" in message and "qa" in message for message in messages))

    def test_validate_repository_reports_missing_status_history_for_done_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["EXEC-2026-001"]
        artifact.header["status"] = "done"
        artifact.header["status_history"] = []

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("EXEC-2026-001" in message and "done" in message for message in messages))

    def test_validate_repository_allows_draft_artifact_without_review_records_or_status_history(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["DESIGN-2026-001"]
        artifact.header["status"] = "draft"
        artifact.header["review_records"] = []
        artifact.header["status_history"] = []

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("DESIGN-2026-001" in message for message in messages))

    def test_validate_repository_reports_invalid_status_transition_in_history(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["EXEC-2026-001"]
        artifact.header["status_history"][1]["to_status"] = "draft"

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("EXEC-2026-001" in message and "approved" in message and "draft" in message for message in messages))

    def test_validate_repository_reports_status_history_sequence_mismatch(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["RELEASE-2026-001"]
        artifact.header["status_history"] = [
            artifact.header["status_history"][1],
            artifact.header["status_history"][0],
            artifact.header["status_history"][2],
        ]

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("RELEASE-2026-001" in message and "sequence" in message for message in messages))

    def test_validate_repository_reports_current_status_mismatch_with_history(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        artifact = repository.artifacts_by_id["PRD-2026-001"]
        artifact.header["status"] = "active"

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("PRD-2026-001" in message and "current status" in message and "done" in message for message in messages))

    def test_validate_repository_allows_draft_successor_without_supersedes_for_immutable_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.2",
            status="draft",
        )

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("PRD-2026-001" in message and "supersedes" in message for message in messages))
        self.assertFalse(any("PRD-2026-002" in message and "supersedes" in message for message in messages))

    def test_validate_repository_allows_in_review_successor_without_supersedes_for_immutable_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.2",
            status="in_review",
        )

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("PRD-2026-001" in message and "supersedes" in message for message in messages))
        self.assertFalse(any("PRD-2026-002" in message and "supersedes" in message for message in messages))

    def test_validate_repository_reports_missing_supersedes_when_successor_becomes_approved(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.2",
            status="approved",
        )

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("PRD-2026-001" in message and "supersedes" in message for message in messages))
        self.assertTrue(any("PRD-2026-002" in message and "supersedes" in message for message in messages))

    def test_validate_repository_accepts_superseded_successor_for_immutable_artifact(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.2",
            status="draft",
        )
        repository.relation_edges_by_id["EDGE-9001"] = {
            "edge_id": "EDGE-9001",
            "relation_type": "supersedes",
            "from": {
                "id": "PRD-2026-002",
                "kind": "artifact",
                "type": "prd_story_pack",
            },
            "to": {
                "id": "PRD-2026-001",
                "kind": "artifact",
                "type": "prd_story_pack",
            },
        }

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("PRD-2026-001" in message and "supersedes" in message for message in messages))
        self.assertFalse(any("PRD-2026-002" in message and "supersedes" in message for message in messages))

    def test_validate_repository_reports_supersedes_edge_with_same_version(self):
        repository, schema, validate_repository = self.load_example_validation_context()

        self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.1",
            status="draft",
        )
        repository.relation_edges_by_id["EDGE-9001"] = {
            "edge_id": "EDGE-9001",
            "relation_type": "supersedes",
            "from": {
                "id": "PRD-2026-002",
                "kind": "artifact",
                "type": "prd_story_pack",
            },
            "to": {
                "id": "PRD-2026-001",
                "kind": "artifact",
                "type": "prd_story_pack",
            },
        }

        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("PRD-2026-002" in message and "same version" in message for message in messages))

    def test_validate_repository_allows_evidence_only_mutation_for_immutable_artifact(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        prd_path = fixture_root / "02_prd.md"
        original = prd_path.read_text(encoding="utf-8")
        updated = original.replace(
            'updated_at: "2026-03-23T18:00:00+08:00"',
            'updated_at: "2026-03-24T09:30:00+08:00"',
        ).replace(
            "change_summary:\n  - Initial end-to-end example PRD",
            "change_summary:\n  - Initial end-to-end example PRD\n  - Added validation evidence after release retrospective",
        )
        prd_path.write_text(updated, encoding="utf-8")

        repository = load_repository([fixture_root])
        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("PRD-2026-001" in message and "immutable" in message for message in messages))

    def test_validate_repository_allows_validation_record_mutation_for_immutable_artifact(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        test_path = fixture_root / "05_test_acceptance.md"
        original = test_path.read_text(encoding="utf-8")
        updated = original.replace(
            'updated_at: "2026-03-23T18:00:00+08:00"',
            'updated_at: "2026-03-24T16:00:00+08:00"',
        ).replace(
            "status_history:\n",
            "validation_records:\n"
            "  - validator_name: qa.smoke\n"
            "    result: pass\n"
            '    recorded_at: "2026-03-24T16:00:00+08:00"\n'
            "    note: Post-release smoke rerun remains green.\n"
            "status_history:\n",
        )
        test_path.write_text(updated, encoding="utf-8")

        repository = load_repository([fixture_root])
        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertFalse(any("TEST-2026-001" in message and "immutable" in message for message in messages))

    def test_validate_repository_reports_protected_header_mutation_for_immutable_artifact(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        prd_path = fixture_root / "02_prd.md"
        original = prd_path.read_text(encoding="utf-8")
        updated = original.replace(
            "title: User Tag Bulk Import PRD",
            "title: User Tag Bulk Import PRD Revised In Place",
        )
        prd_path.write_text(updated, encoding="utf-8")

        repository = load_repository([fixture_root])
        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("PRD-2026-001" in message and "immutable" in message for message in messages))

    def test_validate_repository_reports_trace_unit_mutation_for_immutable_artifact(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        test_path = fixture_root / "05_test_acceptance.md"
        original = test_path.read_text(encoding="utf-8")
        updated = original.replace(
            "statement: Upload a valid CSV, confirm preview and validation output, and verify that no user tag changes happen until the commit action succeeds.",
            "statement: Upload a valid CSV, auto-fix invalid rows during preview, and apply user tag changes without an explicit commit gate.",
        )
        test_path.write_text(updated, encoding="utf-8")

        repository = load_repository([fixture_root])
        issues = validate_repository(repository, schema)

        messages = self.governance_messages(issues)
        self.assertTrue(any("TEST-2026-001" in message and "immutable" in message for message in messages))

    def test_load_head_artifact_uses_noninteractive_git_subprocess_settings(self):
        from traceloom import validators

        artifact_path = EXAMPLE_DIR / "02_prd.md"
        committed_cache = {}
        parsed_artifact = object()

        with (
            mock.patch.object(validators.subprocess, "run") as run_mock,
            mock.patch.object(validators, "parse_artifact_text", return_value=parsed_artifact),
        ):
            run_mock.side_effect = [
                subprocess.CompletedProcess(
                    args=["git"],
                    returncode=0,
                    stdout=str(EXAMPLE_DIR),
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=["git"],
                    returncode=0,
                    stdout="artifact text",
                    stderr="",
                ),
            ]

            committed = validators._load_head_artifact(artifact_path, committed_cache)

        self.assertIs(committed, parsed_artifact)
        self.assertEqual(len(run_mock.call_args_list), 2)

        rev_parse_call = run_mock.call_args_list[0]
        self.assertEqual(
            rev_parse_call.args[0],
            ["git", "-C", str(artifact_path.resolve().parent), "rev-parse", "--show-toplevel"],
        )
        self.assertIs(rev_parse_call.kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(rev_parse_call.kwargs["stdout"], subprocess.PIPE)
        self.assertIs(rev_parse_call.kwargs["stderr"], subprocess.PIPE)
        self.assertTrue(rev_parse_call.kwargs["text"])
        self.assertFalse(rev_parse_call.kwargs["check"])
        self.assertEqual(rev_parse_call.kwargs["timeout"], 5)
        self.assertEqual(rev_parse_call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(rev_parse_call.kwargs["env"]["GIT_PAGER"], "cat")

        show_call = run_mock.call_args_list[1]
        self.assertEqual(
            show_call.args[0],
            ["git", "-C", str(EXAMPLE_DIR), "--no-pager", "show", "HEAD:02_prd.md"],
        )
        self.assertIs(show_call.kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(show_call.kwargs["stdout"], subprocess.PIPE)
        self.assertIs(show_call.kwargs["stderr"], subprocess.PIPE)
        self.assertTrue(show_call.kwargs["text"])
        self.assertFalse(show_call.kwargs["check"])
        self.assertEqual(show_call.kwargs["timeout"], 5)
        self.assertEqual(show_call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(show_call.kwargs["env"]["GIT_PAGER"], "cat")

    def test_validate_repository_skips_git_lookup_timeout_for_immutable_artifacts(self):
        load_repository, load_schema, validate_repository, _ = self.import_runtime()
        schema = load_schema(SCHEMA_PATH)

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        repository = load_repository([fixture_root])

        with mock.patch(
            "traceloom.validators.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=5),
        ):
            issues = validate_repository(repository, schema)

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
