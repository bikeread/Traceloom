from copy import deepcopy
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"


class QueryTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.queries import (
                diff_versions,
                get_artifact,
                get_status_history,
                get_trace_unit,
                list_artifact_versions,
                list_open_questions,
                list_related,
                trace_downstream,
                trace_upstream,
            )
            from traceloom.repository import load_repository
        except ImportError as exc:
            self.fail(f"could not import query runtime: {exc}")
        return (
            load_repository,
            get_artifact,
            get_trace_unit,
            list_related,
            trace_upstream,
            trace_downstream,
            get_status_history,
            list_open_questions,
            list_artifact_versions,
            diff_versions,
        )

    def load_example_repository(self):
        (
            load_repository,
            get_artifact,
            get_trace_unit,
            list_related,
            trace_upstream,
            trace_downstream,
            get_status_history,
            list_open_questions,
            list_artifact_versions,
            diff_versions,
        ) = self.import_runtime()
        repository = load_repository([EXAMPLE_DIR])
        return (
            repository,
            get_artifact,
            get_trace_unit,
            list_related,
            trace_upstream,
            trace_downstream,
            get_status_history,
            list_open_questions,
            list_artifact_versions,
            diff_versions,
        )

    def load_versioned_example_repository(self):
        (
            load_repository,
            get_artifact,
            get_trace_unit,
            list_related,
            trace_upstream,
            trace_downstream,
            get_status_history,
            list_open_questions,
            list_artifact_versions,
            diff_versions,
        ) = self.import_runtime()
        repository = load_repository([VERSIONED_EXAMPLE_DIR])
        return (
            repository,
            get_artifact,
            get_trace_unit,
            list_related,
            trace_upstream,
            trace_downstream,
            get_status_history,
            list_open_questions,
            list_artifact_versions,
            diff_versions,
        )

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
        clone = source.__class__(
            path=EXAMPLE_DIR / f"{new_artifact_id.lower()}.md",
            header=header,
            body=source.body,
            headings=list(source.headings),
            trace_units=deepcopy(source.trace_units),
            relation_edges=[],
        )
        repository.artifacts_by_id[new_artifact_id] = clone
        return clone

    def test_get_artifact_supports_header_trace_only_and_full_views(self):
        (
            repository,
            get_artifact,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
        ) = self.load_example_repository()

        header_view = get_artifact(repository, "PRD-2026-001", view="header")
        trace_view = get_artifact(repository, "PRD-2026-001", view="trace_only")
        full_view = get_artifact(repository, "PRD-2026-001", view="full")

        self.assertEqual(header_view["artifact_id"], "PRD-2026-001")
        self.assertIn("header", header_view)
        self.assertNotIn("body", header_view)
        self.assertEqual(trace_view["trace_units"][0]["id"], "REQ-001")
        self.assertIn("relation_edges", trace_view)
        self.assertIn("body", full_view)
        self.assertEqual(full_view["artifact_type"], "prd_story_pack")

    def test_get_trace_unit_returns_parent_context(self):
        (
            repository,
            _,
            get_trace_unit,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
        ) = self.load_example_repository()

        result = get_trace_unit(repository, "DEC-001")

        self.assertEqual(result["artifact_id"], "DESIGN-2026-001")
        self.assertEqual(result["artifact_type"], "solution_design")
        self.assertEqual(result["unit"]["id"], "DEC-001")

    def test_list_related_filters_by_direction_and_relation_type(self):
        (
            repository,
            _,
            _,
            list_related,
            _,
            _,
            _,
            _,
            _,
            _,
        ) = self.load_example_repository()

        related = list_related(repository, "REQ-001", direction="downstream", relation_type="refines")

        self.assertEqual([item["related_id"] for item in related], ["AC-001"])
        self.assertEqual(related[0]["direction"], "downstream")
        self.assertEqual(related[0]["relation_type"], "refines")

    def test_trace_upstream_and_downstream_follow_graph(self):
        (
            repository,
            _,
            _,
            _,
            trace_upstream,
            trace_downstream,
            _,
            _,
            _,
            _,
        ) = self.load_example_repository()

        upstream = trace_upstream(repository, "REV-001")
        downstream = trace_downstream(repository, "GOAL-001")

        self.assertIn("REL-001", upstream)
        self.assertIn("GOAL-001", upstream)
        self.assertIn("REV-001", downstream)
        self.assertIn("REQ-001", downstream)

    def test_get_status_history_returns_artifact_records(self):
        (
            repository,
            _,
            _,
            _,
            _,
            _,
            get_status_history,
            _,
            _,
            _,
        ) = self.load_example_repository()

        history = get_status_history(repository, "PRD-2026-001")

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["to_status"], "approved")
        self.assertEqual(history[-1]["to_status"], "done")

    def test_list_open_questions_filters_by_artifact_and_status(self):
        (
            repository,
            _,
            _,
            _,
            _,
            _,
            _,
            list_open_questions,
            _,
            _,
        ) = self.load_example_repository()

        repository.artifacts_by_id["DESIGN-2026-001"].header["open_questions"] = [
            {"q_id": "Q-101", "status": "open", "note": "Need rollback scope."},
            {"q_id": "Q-102", "status": "resolved", "note": "Preview storage decision closed."},
        ]

        all_questions = list_open_questions(repository)
        open_questions = list_open_questions(repository, artifact_id="DESIGN-2026-001", status="open")

        self.assertEqual(len(all_questions), 2)
        self.assertEqual([item["q_id"] for item in open_questions], ["Q-101"])
        self.assertEqual(open_questions[0]["artifact_id"], "DESIGN-2026-001")

    def test_list_artifact_versions_and_diff_versions_use_family_context(self):
        (
            repository,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            list_artifact_versions,
            diff_versions,
        ) = self.load_example_repository()

        successor = self.add_artifact_version_clone(
            repository,
            "PRD-2026-001",
            new_artifact_id="PRD-2026-002",
            version="v0.2",
            status="draft",
        )
        successor.header["summary"] = "Refined PRD with retry and version-aware governance."
        successor.trace_units[0]["statement"] = "The system must support CSV import with retry-safe commit behavior."

        versions = list_artifact_versions(repository, "PRD-2026-001")
        diff = diff_versions(repository, "PRD-2026-001", "v0.1", "v0.2")

        self.assertEqual([item["version"] for item in versions], ["v0.1", "v0.2"])

    def test_list_artifact_versions_and_diff_versions_work_for_committed_versioned_example(self):
        self.assertTrue(VERSIONED_EXAMPLE_DIR.is_dir())

        (
            repository,
            _,
            _,
            _,
            _,
            _,
            _,
            _,
            list_artifact_versions,
            diff_versions,
        ) = self.load_versioned_example_repository()

        versions = list_artifact_versions(repository, "RELEASE-2026-001")
        diff = diff_versions(repository, "RELEASE-2026-001", "v0.1", "v0.2")

        self.assertEqual([item["artifact_id"] for item in versions], ["RELEASE-2026-001", "RELEASE-2026-002"])
        self.assertEqual([item["version"] for item in versions], ["v0.1", "v0.2"])
        self.assertEqual(diff["from_artifact_id"], "RELEASE-2026-001")
        self.assertEqual(diff["to_artifact_id"], "RELEASE-2026-002")
        self.assertIn("summary", diff["changed_header_fields"])
        self.assertIn("REL-002", diff["changed_trace_unit_ids"])

    def test_committed_versioned_example_exposes_successor_versions_across_core_families(self):
        self.assertTrue(VERSIONED_EXAMPLE_DIR.is_dir())

        (
            repository,
            _,
            _,
            _,
            _,
            trace_downstream,
            _,
            _,
            list_artifact_versions,
            diff_versions,
        ) = self.load_versioned_example_repository()

        brief_versions = list_artifact_versions(repository, "BRIEF-2026-001")
        prd_versions = list_artifact_versions(repository, "PRD-2026-001")
        design_versions = list_artifact_versions(repository, "DESIGN-2026-001")
        exec_versions = list_artifact_versions(repository, "EXEC-2026-001")
        test_versions = list_artifact_versions(repository, "TEST-2026-001")
        brief_diff = diff_versions(repository, "BRIEF-2026-001", "v0.1", "v0.2")
        prd_diff = diff_versions(repository, "PRD-2026-001", "v0.1", "v0.2")
        successor_downstream = trace_downstream(repository, "GOAL-002")

        self.assertEqual([item["artifact_id"] for item in brief_versions], ["BRIEF-2026-001", "BRIEF-2026-002"])
        self.assertEqual([item["artifact_id"] for item in prd_versions], ["PRD-2026-001", "PRD-2026-002"])
        self.assertEqual([item["artifact_id"] for item in design_versions], ["DESIGN-2026-001", "DESIGN-2026-002"])
        self.assertEqual([item["artifact_id"] for item in exec_versions], ["EXEC-2026-001", "EXEC-2026-002"])
        self.assertEqual([item["artifact_id"] for item in test_versions], ["TEST-2026-001", "TEST-2026-002"])
        self.assertIn("GOAL-002", brief_diff["changed_trace_unit_ids"])
        self.assertIn("REQ-002", prd_diff["changed_trace_unit_ids"])
        self.assertIn("REQ-002", successor_downstream)
        self.assertIn("REV-002", successor_downstream)


if __name__ == "__main__":
    unittest.main()
