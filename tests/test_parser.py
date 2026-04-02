from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"


class ParserTests(unittest.TestCase):
    def import_parser(self):
        try:
            from traceloom.parser import parse_artifact
        except ImportError as exc:
            self.fail(f"could not import traceloom.parser.parse_artifact: {exc}")
        return parse_artifact

    def test_parse_brief_frontmatter(self):
        parse_artifact = self.import_parser()

        artifact = parse_artifact(EXAMPLE_DIR / "01_brief.md")

        self.assertEqual(artifact.artifact_id, "BRIEF-2026-001")
        self.assertEqual(artifact.artifact_type, "brief")
        self.assertEqual(artifact.title, "User Tag Bulk Import Brief")
        self.assertEqual(artifact.status, "done")
        self.assertEqual(artifact.scope["feature_key"], "user-tag-bulk-import")

    def test_parse_trace_units_from_yaml_block(self):
        parse_artifact = self.import_parser()

        artifact = parse_artifact(EXAMPLE_DIR / "01_brief.md")

        self.assertEqual(len(artifact.trace_units), 1)
        unit = artifact.trace_units[0]
        self.assertEqual(unit["id"], "GOAL-001")
        self.assertEqual(unit["type"], "GOAL")

    def test_parse_relation_edges_from_yaml_block(self):
        parse_artifact = self.import_parser()

        artifact = parse_artifact(EXAMPLE_DIR / "02_prd.md")

        edge_ids = [edge["edge_id"] for edge in artifact.relation_edges]
        self.assertEqual(edge_ids, ["EDGE-0001", "EDGE-0002"])


if __name__ == "__main__":
    unittest.main()
