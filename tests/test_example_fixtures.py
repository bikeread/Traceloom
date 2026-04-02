from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"
INVALID_FIXTURE_ROOT = REPO_ROOT / "examples" / "invalid"


class ExampleFixtureTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.repository import load_repository
            from traceloom.validators import load_schema, validate_repository
        except ImportError as exc:
            self.fail(f"could not import fixture-validation runtime: {exc}")
        return load_repository, load_schema, validate_repository

    def validate_fixture(self, fixture_name: str) -> list[str]:
        load_repository, load_schema, validate_repository = self.import_runtime()
        fixture_dir = INVALID_FIXTURE_ROOT / fixture_name

        self.assertTrue(fixture_dir.is_dir(), fixture_name)

        schema = load_schema(SCHEMA_PATH)
        repository = load_repository([fixture_dir])
        issues = validate_repository(repository, schema)
        return [issue.code for issue in issues]

    def test_invalid_fixture_trace_unit_id_pattern_reports_invalid_pattern(self):
        issue_codes = self.validate_fixture("trace-unit-id-pattern")

        self.assertIn("invalid_pattern", issue_codes)

    def test_invalid_fixture_typed_ref_target_type_reports_typed_ref_mismatch(self):
        issue_codes = self.validate_fixture("typed-ref-target-type-mismatch")

        self.assertIn("typed_ref_target_type_mismatch", issue_codes)

    def test_invalid_fixture_relation_endpoint_type_reports_relation_endpoint_mismatch(self):
        issue_codes = self.validate_fixture("relation-endpoint-type-mismatch")

        self.assertIn("relation_endpoint_type_mismatch", issue_codes)

    def test_invalid_fixture_illegal_status_transition_reports_invalid_status_transition(self):
        issue_codes = self.validate_fixture("illegal-status-transition")

        self.assertIn("invalid_status_transition", issue_codes)

    def test_invalid_fixture_missing_supersedes_link_reports_missing_supersedes_link(self):
        issue_codes = self.validate_fixture("missing-supersedes-link")

        self.assertIn("missing_supersedes_link", issue_codes)

    def test_invalid_fixture_supersedes_same_version_reports_same_version_issue(self):
        issue_codes = self.validate_fixture("supersedes-same-version")

        self.assertIn("supersedes_same_version", issue_codes)


if __name__ == "__main__":
    unittest.main()
