from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class SchemaContractTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.validators import load_schema
        except ImportError as exc:
            self.fail(f"could not import schema runtime: {exc}")
        return load_schema

    def test_schema_write_operations_match_track_a_canonical_action_names(self):
        load_schema = self.import_runtime()

        schema = load_schema(SCHEMA_PATH)

        self.assertEqual(
            sorted(schema["minimal_ai_access_model"]["write_operations"].keys()),
            [
                "create_artifact_draft",
                "promote_artifact_status",
                "record_review_decision",
                "record_validation_result",
                "revise_artifact_draft",
                "supersede_artifact_version",
            ],
        )


if __name__ == "__main__":
    unittest.main()
