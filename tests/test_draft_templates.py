from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


class DraftTemplateTests(unittest.TestCase):
    def import_runtime(self):
        try:
            from traceloom.draft_templates import render_artifact_scaffold
            from traceloom.validators import load_schema
        except ImportError as exc:
            self.fail(f"could not import draft template runtime: {exc}")
        return render_artifact_scaffold, load_schema

    def test_render_artifact_scaffold_includes_required_sections_for_prd(self):
        render_artifact_scaffold, load_schema = self.import_runtime()

        schema = load_schema(SCHEMA_PATH)
        body = render_artifact_scaffold(schema, "prd_story_pack")

        self.assertIn("## User Scenarios", body)
        self.assertIn("## Acceptance Criteria", body)
        self.assertIn("## Trace Units", body)
        self.assertIn("## Relation Edges", body)
        self.assertEqual(body.count("```yaml\n[]\n```"), 2)
        self.assertLess(body.index("## User Scenarios"), body.index("## Acceptance Criteria"))
        self.assertLess(body.index("## Acceptance Criteria"), body.index("## Trace Units"))


if __name__ == "__main__":
    unittest.main()
