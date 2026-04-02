from pathlib import Path
import unittest

from tests.git_fixture_helpers import init_git_example_repo


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class WriteOpsTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.artifact_io import write_artifact_header
            from traceloom.parser import parse_artifact
            from traceloom.repository import load_repository
            from traceloom.validators import load_schema, validate_repository
            from traceloom.write_ops import (
                create_artifact_draft,
                promote_artifact_status,
                record_review_decision,
                record_validation_result,
                revise_artifact_draft,
                supersede_artifact_version,
            )
        except ImportError as exc:
            self.fail(f"could not import write ops runtime: {exc}")
        return (
            write_artifact_header,
            parse_artifact,
            load_repository,
            load_schema,
            validate_repository,
            create_artifact_draft,
            revise_artifact_draft,
            supersede_artifact_version,
            record_review_decision,
            record_validation_result,
            promote_artifact_status,
        )

    def test_create_artifact_draft_writes_scaffolded_prd_file(self):
        _, parse_artifact, load_repository, load_schema, validate_repository, create_artifact_draft, _, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = create_artifact_draft(
            fixture_root,
            relative_path="12_prd_v0_2.md",
            artifact_type="prd_story_pack",
            artifact_id="PRD-2026-002",
            title="Retry-Safe Bulk Import PRD",
            summary="Revise the requirement contract for retry-safe commit semantics.",
            version="v0.2",
            owner={
                "actor_id": "user:li.pm",
                "role": "pm",
            },
            scope={
                "product_area": "growth",
                "feature_key": "user-tag-bulk-import",
                "in_scope": ["retry-safe commit"],
            },
            created_at="2026-03-25T09:00:00+08:00",
        )

        artifact = parse_artifact(fixture_root / "12_prd_v0_2.md")
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "PRD-2026-002")
        self.assertEqual(result["status"], "draft")
        self.assertEqual(artifact.header["status"], "draft")
        self.assertEqual(artifact.header["version"], "v0.2")
        self.assertIn("## User Scenarios", artifact.body)
        self.assertIn("## Trace Units", artifact.body)
        self.assertFalse(any(issue.object_id == "PRD-2026-002" for issue in issues))

    def test_create_artifact_draft_rejects_duplicate_artifact_id_before_file_mutation(self):
        _, _, _, _, _, create_artifact_draft, _, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "12_prd_v0_2.md"

        with self.assertRaises(ValueError):
            create_artifact_draft(
                fixture_root,
                relative_path="12_prd_v0_2.md",
                artifact_type="prd_story_pack",
                artifact_id="PRD-2026-001",
                title="Duplicate PRD",
                summary="This should be rejected.",
                version="v0.2",
                owner={
                    "actor_id": "user:li.pm",
                    "role": "pm",
                },
                scope={
                    "product_area": "growth",
                    "feature_key": "user-tag-bulk-import",
                    "in_scope": ["retry-safe commit"],
                },
                created_at="2026-03-25T09:00:00+08:00",
            )

        self.assertFalse(target.exists())

    def test_revise_artifact_draft_updates_body_for_draft_artifact(self):
        _, parse_artifact, load_repository, load_schema, validate_repository, _, revise_artifact_draft, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(VERSIONED_EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "08_prd_v0_2.md"
        artifact = parse_artifact(target)

        result = revise_artifact_draft(
            fixture_root,
            artifact_id="PRD-2026-002",
            body=artifact.body.replace(
                "reviews a preview, retries safely after transient failures, and then commits the import.",
                "reviews a preview, retries safely after transient failures, and only commits after explicit operator confirmation.",
            ),
            header_updates={
                "summary": "Updated draft summary.",
            },
            updated_at="2026-03-25T10:00:00+08:00",
        )

        artifact = parse_artifact(target)
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "PRD-2026-002")
        self.assertEqual(result["status"], "draft")
        self.assertEqual(artifact.header["summary"], "Updated draft summary.")
        self.assertIn("only commits after explicit operator confirmation", artifact.body)
        self.assertFalse(any(issue.object_id == "PRD-2026-002" for issue in issues))

    def test_revise_artifact_draft_updates_body_for_in_review_artifact(self):
        write_artifact_header, parse_artifact, load_repository, load_schema, validate_repository, _, revise_artifact_draft, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(VERSIONED_EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "08_prd_v0_2.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "in_review"
        header["updated_at"] = "2026-03-25T09:45:00+08:00"
        write_artifact_header(target, header)

        result = revise_artifact_draft(
            fixture_root,
            artifact_id="PRD-2026-002",
            body=artifact.body.replace(
                "Document retry-safe commit expectations",
                "Document retry-safe commit expectations and operator rollback guidance",
            ),
            header_updates={
                "summary": "Updated in-review summary.",
            },
            updated_at="2026-03-25T10:15:00+08:00",
        )

        artifact = parse_artifact(target)
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "PRD-2026-002")
        self.assertEqual(result["status"], "in_review")
        self.assertEqual(artifact.header["summary"], "Updated in-review summary.")
        self.assertIn("operator rollback guidance", artifact.body)
        self.assertFalse(any(issue.object_id == "PRD-2026-002" for issue in issues))

    def test_revise_artifact_draft_rejects_immutable_artifact_before_mutation(self):
        _, _, _, _, _, _, revise_artifact_draft, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "02_prd.md"
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            revise_artifact_draft(
                fixture_root,
                artifact_id="PRD-2026-001",
                body="## User Scenarios\n\nThis mutation should be rejected.\n",
                header_updates={"summary": "Rejected immutable revision."},
                updated_at="2026-03-25T10:30:00+08:00",
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_revise_artifact_draft_rejects_invalid_revision_before_file_mutation(self):
        write_artifact_header, parse_artifact, _, _, _, _, revise_artifact_draft, _, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(VERSIONED_EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "08_prd_v0_2.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "in_review"
        header["updated_at"] = "2026-03-25T09:45:00+08:00"
        write_artifact_header(target, header)
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            revise_artifact_draft(
                fixture_root,
                artifact_id="PRD-2026-002",
                body="## User Scenarios\n\nBroken revision.\n",
                header_updates={"summary": "Broken in-review summary."},
                updated_at="2026-03-25T10:45:00+08:00",
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_supersede_artifact_version_appends_artifact_level_edge(self):
        _, parse_artifact, load_repository, load_schema, validate_repository, create_artifact_draft, _, supersede_artifact_version, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        create_artifact_draft(
            fixture_root,
            relative_path="12_prd_v0_2.md",
            artifact_type="prd_story_pack",
            artifact_id="PRD-2026-002",
            title="Retry-Safe Bulk Import PRD",
            summary="Revise the requirement contract for retry-safe commit semantics.",
            version="v0.2",
            owner={
                "actor_id": "user:li.pm",
                "role": "pm",
            },
            scope={
                "product_area": "growth",
                "feature_key": "user-tag-bulk-import",
                "in_scope": ["retry-safe commit"],
            },
            created_at="2026-03-25T11:00:00+08:00",
        )

        result = supersede_artifact_version(
            fixture_root,
            successor_artifact_id="PRD-2026-002",
            predecessor_artifact_id="PRD-2026-001",
            edge_id="EDGE-2003",
            created_at="2026-03-25T11:10:00+08:00",
            created_by={
                "actor_id": "user:li.pm",
                "role": "pm",
                "capability": "artifact_governance",
                "decision_authority": "prd_owner",
            },
        )

        artifact = parse_artifact(fixture_root / "12_prd_v0_2.md")
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "PRD-2026-002")
        self.assertEqual(result["updated_field"], "relation_edges")
        self.assertEqual(artifact.relation_edges[-1]["relation_type"], "supersedes")
        self.assertEqual(artifact.relation_edges[-1]["from"]["id"], "PRD-2026-002")
        self.assertEqual(artifact.relation_edges[-1]["to"]["id"], "PRD-2026-001")
        self.assertEqual(artifact.relation_edges[-1]["created_by"]["capability"], "artifact_governance")
        self.assertEqual(artifact.relation_edges[-1]["created_by"]["decision_authority"], "prd_owner")
        self.assertFalse(any(issue.object_id == "PRD-2026-002" for issue in issues))

    def test_supersede_artifact_version_rejects_same_version_before_file_mutation(self):
        _, _, _, _, _, create_artifact_draft, _, supersede_artifact_version, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "12_prd_v0_2.md"
        create_artifact_draft(
            fixture_root,
            relative_path="12_prd_v0_2.md",
            artifact_type="prd_story_pack",
            artifact_id="PRD-2026-002",
            title="Retry-Safe Bulk Import PRD",
            summary="Revise the requirement contract for retry-safe commit semantics.",
            version="v0.1",
            owner={
                "actor_id": "user:li.pm",
                "role": "pm",
            },
            scope={
                "product_area": "growth",
                "feature_key": "user-tag-bulk-import",
                "in_scope": ["retry-safe commit"],
            },
            created_at="2026-03-25T11:00:00+08:00",
        )
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            supersede_artifact_version(
                fixture_root,
                successor_artifact_id="PRD-2026-002",
                predecessor_artifact_id="PRD-2026-001",
                edge_id="EDGE-2003",
                created_at="2026-03-25T11:15:00+08:00",
                created_by={
                    "actor_id": "user:li.pm",
                    "role": "pm",
                },
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_supersede_artifact_version_rejects_cross_type_before_file_mutation(self):
        _, _, _, _, _, create_artifact_draft, _, supersede_artifact_version, _, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "12_design_v0_2.md"
        create_artifact_draft(
            fixture_root,
            relative_path="12_design_v0_2.md",
            artifact_type="solution_design",
            artifact_id="DESIGN-2026-002",
            title="Retry-Safe Bulk Import Design",
            summary="Draft design successor for retry-safe commit semantics.",
            version="v0.2",
            owner={
                "actor_id": "user:zhou.tl",
                "role": "tech_lead",
            },
            scope={
                "product_area": "growth",
                "feature_key": "user-tag-bulk-import",
                "in_scope": ["retry-safe commit"],
            },
            created_at="2026-03-25T11:00:00+08:00",
        )
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            supersede_artifact_version(
                fixture_root,
                successor_artifact_id="DESIGN-2026-002",
                predecessor_artifact_id="PRD-2026-001",
                edge_id="EDGE-2003",
                created_at="2026-03-25T11:20:00+08:00",
                created_by={
                    "actor_id": "user:zhou.tl",
                    "role": "tech_lead",
                },
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_record_review_decision_appends_review_record(self):
        _, parse_artifact, _, _, _, _, _, _, record_review_decision, _, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = record_review_decision(
            fixture_root,
            artifact_id="DESIGN-2026-001",
            review_record={
                "reviewer": {
                    "actor_id": "user:zhou.tl",
                    "role": "tech_lead",
                },
                "decision": "approve",
                "recorded_at": "2026-03-24T15:00:00+08:00",
            },
        )

        artifact = parse_artifact(fixture_root / "03_solution_design.md")

        self.assertEqual(result["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(result["updated_field"], "review_records")
        self.assertEqual(artifact.header["review_records"][-1]["decision"], "approve")
        self.assertEqual(artifact.header["review_records"][-1]["reviewer"]["actor_id"], "user:zhou.tl")

    def test_record_validation_result_appends_validation_record_and_keeps_repo_valid(self):
        _, parse_artifact, load_repository, load_schema, validate_repository, _, _, _, _, record_validation_result, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        result = record_validation_result(
            fixture_root,
            artifact_id="TEST-2026-001",
            validation_record={
                "validator_name": "qa.smoke",
                "result": "pass",
                "recorded_at": "2026-03-24T16:00:00+08:00",
                "note": "Post-release smoke rerun remains green.",
            },
        )

        artifact = parse_artifact(fixture_root / "05_test_acceptance.md")
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "TEST-2026-001")
        self.assertEqual(result["updated_field"], "validation_records")
        self.assertEqual(artifact.header["validation_records"][-1]["validator_name"], "qa.smoke")
        self.assertFalse(any(issue.object_id == "TEST-2026-001" for issue in issues))

    def test_record_validation_result_rejects_malformed_payload_before_file_mutation(self):
        _, _, _, _, _, _, _, _, _, record_validation_result, _ = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "05_test_acceptance.md"
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            record_validation_result(
                fixture_root,
                artifact_id="TEST-2026-001",
                validation_record={
                    "validator_name": ["qa.smoke"],
                    "result": "pass",
                    "recorded_at": "not-a-datetime",
                },
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_promote_artifact_status_appends_status_history_and_updates_status(self):
        write_artifact_header, parse_artifact, load_repository, load_schema, validate_repository, _, _, _, _, _, promote_artifact_status = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "03_solution_design.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "approved"
        header["updated_at"] = "2026-03-24T15:30:00+08:00"
        header["status_history"] = [artifact.header["status_history"][0]]
        write_artifact_header(target, header)

        result = promote_artifact_status(
            fixture_root,
            artifact_id="DESIGN-2026-001",
            target_status="active",
            changed_by={
                "actor_id": "user:zhou.tl",
                "role": "tech_lead",
            },
            changed_at="2026-03-24T16:00:00+08:00",
        )

        artifact = parse_artifact(target)
        repository = load_repository([fixture_root])
        schema = load_schema(SCHEMA_PATH)
        issues = validate_repository(repository, schema)

        self.assertEqual(result["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(result["status"], "active")
        self.assertEqual(artifact.header["status"], "active")
        self.assertEqual(artifact.header["status_history"][-1]["to_status"], "active")
        self.assertFalse(any(issue.object_id == "DESIGN-2026-001" for issue in issues))

    def test_promote_artifact_status_rejects_invalid_transition(self):
        write_artifact_header, parse_artifact, _, _, _, _, _, _, _, _, promote_artifact_status = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "03_solution_design.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "approved"
        header["updated_at"] = "2026-03-24T15:30:00+08:00"
        header["status_history"] = [artifact.header["status_history"][0]]
        write_artifact_header(target, header)
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            promote_artifact_status(
                fixture_root,
                artifact_id="DESIGN-2026-001",
                target_status="draft",
                changed_by={
                    "actor_id": "user:zhou.tl",
                    "role": "tech_lead",
                },
                changed_at="2026-03-24T16:05:00+08:00",
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_promote_artifact_status_requires_review_evidence_before_approval(self):
        write_artifact_header, parse_artifact, _, _, _, _, _, _, _, _, promote_artifact_status = self.import_runtime()

        temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
        self.addCleanup(temp_dir.cleanup)

        target = fixture_root / "02_prd.md"
        artifact = parse_artifact(target)
        header = dict(artifact.header)
        header["status"] = "in_review"
        header["updated_at"] = "2026-03-24T15:30:00+08:00"
        header["review_records"] = []
        header["status_history"] = []
        write_artifact_header(target, header)
        original = target.read_text(encoding="utf-8")

        with self.assertRaises(ValueError):
            promote_artifact_status(
                fixture_root,
                artifact_id="PRD-2026-001",
                target_status="approved",
                changed_by={
                    "actor_id": "user:li.pm",
                    "role": "pm",
                },
                changed_at="2026-03-24T16:10:00+08:00",
            )

        self.assertEqual(target.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
