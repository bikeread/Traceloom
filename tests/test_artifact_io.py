from pathlib import Path
import tempfile
import unittest


class ArtifactIoTests(unittest.TestCase):
    SAMPLE_TEXT = (
        "---\n"
        "artifact_id: PRD-2026-001\n"
        "artifact_type: prd_story_pack\n"
        "title: Example PRD\n"
        "summary: Example summary.\n"
        "status: draft\n"
        "version: v0.1\n"
        "owner:\n"
        "  actor_id: user:alice\n"
        "  role: pm\n"
        "created_at: 2026-03-24T09:00:00+08:00\n"
        "updated_at: 2026-03-24T09:00:00+08:00\n"
        "scope:\n"
        "  product_area: growth\n"
        "  feature_key: example\n"
        "  in_scope:\n"
        "    - demo\n"
        "---\n\n"
        "## Scope\n\n"
        "Body stays here.\n"
    )
    SAMPLE_STRUCTURED_BODY = (
        "## Scope\n\n"
        "Body stays here.\n\n"
        "## Trace Units\n\n"
        "```yaml\n"
        "- id: REQ-001\n"
        "  type: REQ\n"
        "  title: Example requirement\n"
        "  statement: Example requirement statement.\n"
        "```\n\n"
        "## Relation Edges\n\n"
        "```yaml\n"
        "- edge_id: EDGE-0001\n"
        "  relation_type: refines\n"
        "  from:\n"
        "    id: GOAL-001\n"
        "    kind: trace_unit\n"
        "  to:\n"
        "    id: REQ-001\n"
        "    kind: trace_unit\n"
        "```\n"
    )

    def import_runtime(self):
        try:
            from traceloom.artifact_io import (
                read_artifact_parts,
                render_artifact_text,
                replace_relation_edges_block,
                write_artifact_document,
                write_artifact_header,
            )
            from traceloom.parser import parse_artifact, parse_artifact_text
        except ImportError as exc:
            self.fail(f"could not import artifact I/O runtime: {exc}")
        return (
            read_artifact_parts,
            render_artifact_text,
            replace_relation_edges_block,
            write_artifact_document,
            write_artifact_header,
            parse_artifact,
            parse_artifact_text,
        )

    def test_read_artifact_parts_splits_frontmatter_and_body(self):
        read_artifact_parts, _, _, _, _, _, _ = self.import_runtime()

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "artifact.md"
            target.write_text(self.SAMPLE_TEXT, encoding="utf-8")

            header, body = read_artifact_parts(target)

        self.assertEqual(header["artifact_id"], "PRD-2026-001")
        self.assertEqual(header["status"], "draft")
        self.assertEqual(body, "## Scope\n\nBody stays here.\n")

    def test_render_artifact_text_round_trips_header_and_body(self):
        _, render_artifact_text, _, _, _, _, parse_artifact_text = self.import_runtime()

        header = {
            "artifact_id": "PRD-2026-001",
            "artifact_type": "prd_story_pack",
            "title": "Example PRD",
            "summary": "Example summary.",
            "status": "draft",
            "version": "v0.1",
            "owner": {
                "actor_id": "user:alice",
                "role": "pm",
            },
            "created_at": "2026-03-24T09:00:00+08:00",
            "updated_at": "2026-03-24T09:00:00+08:00",
            "scope": {
                "product_area": "growth",
                "feature_key": "example",
                "in_scope": ["demo"],
            },
        }
        body = "## Scope\n\nBody stays here.\n"

        rendered = render_artifact_text(header, body)
        artifact = parse_artifact_text(rendered, path=Path("artifact.md"))

        self.assertEqual(artifact.header["artifact_id"], "PRD-2026-001")
        self.assertEqual(artifact.header["status"], "draft")
        self.assertEqual(artifact.body, body)

    def test_write_artifact_header_preserves_body_sections(self):
        _, _, _, _, write_artifact_header, parse_artifact, _ = self.import_runtime()

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "artifact.md"
            target.write_text(self.SAMPLE_TEXT, encoding="utf-8")

            write_artifact_header(
                target,
                {
                    "artifact_id": "PRD-2026-001",
                    "artifact_type": "prd_story_pack",
                    "title": "Example PRD",
                    "summary": "Example summary.",
                    "status": "in_review",
                    "version": "v0.1",
                    "owner": {
                        "actor_id": "user:alice",
                        "role": "pm",
                    },
                    "created_at": "2026-03-24T09:00:00+08:00",
                    "updated_at": "2026-03-24T09:30:00+08:00",
                    "scope": {
                        "product_area": "growth",
                        "feature_key": "example",
                        "in_scope": ["demo"],
                    },
                },
            )

            reparsed = parse_artifact(target)
            text = target.read_text(encoding="utf-8")

        self.assertEqual(reparsed.header["status"], "in_review")
        self.assertIn("## Scope", reparsed.body)
        self.assertIn("Body stays here.", reparsed.body)
        self.assertIn("## Scope", text)

    def test_replace_relation_edges_block_preserves_narrative_sections(self):
        _, _, replace_relation_edges_block, _, _, _, _ = self.import_runtime()

        updated = replace_relation_edges_block(
            self.SAMPLE_STRUCTURED_BODY,
            [
                {
                    "edge_id": "EDGE-0002",
                    "relation_type": "refines",
                    "from": {
                        "id": "GOAL-001",
                        "kind": "trace_unit",
                    },
                    "to": {
                        "id": "REQ-002",
                        "kind": "trace_unit",
                    },
                }
            ],
        )

        self.assertIn("## Scope", updated)
        self.assertIn("Body stays here.", updated)
        self.assertIn("EDGE-0002", updated)
        self.assertNotIn("EDGE-0001", updated)

    def test_write_artifact_document_replaces_body_text(self):
        _, _, _, write_artifact_document, _, parse_artifact, _ = self.import_runtime()

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "artifact.md"
            target.write_text(self.SAMPLE_TEXT, encoding="utf-8")

            header = {
                "artifact_id": "PRD-2026-001",
                "artifact_type": "prd_story_pack",
                "title": "Example PRD",
                "summary": "Example summary.",
                "status": "draft",
                "version": "v0.1",
                "owner": {
                    "actor_id": "user:alice",
                    "role": "pm",
                },
                "created_at": "2026-03-24T09:00:00+08:00",
                "updated_at": "2026-03-24T09:45:00+08:00",
                "scope": {
                    "product_area": "growth",
                    "feature_key": "example",
                    "in_scope": ["demo"],
                },
            }

            write_artifact_document(target, header, self.SAMPLE_STRUCTURED_BODY)

            reparsed = parse_artifact(target)

        self.assertEqual(reparsed.body, self.SAMPLE_STRUCTURED_BODY)
        self.assertIn("## Relation Edges", reparsed.body)


if __name__ == "__main__":
    unittest.main()
