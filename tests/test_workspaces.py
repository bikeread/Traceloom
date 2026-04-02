from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest


class WorkspaceTests(unittest.TestCase):
    def test_create_workspace_from_starter_defaults_to_minimal_template_and_metadata(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter, get_workspace, list_workspaces
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            workspace = create_workspace_from_starter("billing-intake", root=root)

            self.assertEqual(workspace.name, "billing-intake")
            self.assertEqual(workspace.root_path, root.resolve())
            self.assertEqual(workspace.source_kind, "minimal_requirement_template")
            self.assertEqual(workspace.active_repository_path, root.resolve() / "billing-intake")

            for relative_path in ("README.md", "01_brief.md"):
                self.assertTrue((workspace.active_repository_path / relative_path).is_file(), relative_path)
            for relative_path in (
                "02_prd.md",
                "03_solution_design.md",
                "04_execution_plan.md",
                "05_test_acceptance.md",
                "06_release_review.md",
            ):
                self.assertFalse((workspace.active_repository_path / relative_path).exists(), relative_path)

            self.assertTrue(workspace.metadata_path.is_file())

            listed = list_workspaces(root=root)
            self.assertEqual([item.name for item in listed], ["billing-intake"])
            self.assertEqual(listed[0].active_repository_path, workspace.active_repository_path)

            shown = get_workspace("billing-intake", root=root)
            self.assertEqual(shown.name, workspace.name)
            self.assertEqual(shown.root_path, workspace.root_path)
            self.assertEqual(shown.active_repository_path, workspace.active_repository_path)
            self.assertEqual(shown.source_kind, workspace.source_kind)

    def test_create_workspace_from_starter_materializes_full_template_when_requested(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            workspace = create_workspace_from_starter("billing-intake", root=root, template="full")

            self.assertEqual(workspace.source_kind, "starter_template")
            for relative_path in (
                "README.md",
                "01_brief.md",
                "02_prd.md",
                "03_solution_design.md",
                "04_execution_plan.md",
                "05_test_acceptance.md",
                "06_release_review.md",
            ):
                self.assertTrue((workspace.active_repository_path / relative_path).is_file(), relative_path)

    def test_create_workspace_from_starter_rejects_duplicate_names(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            create_workspace_from_starter("billing-intake", root=root)

            with self.assertRaises(ValueError) as ctx:
                create_workspace_from_starter("billing-intake", root=root)

        self.assertIn("billing-intake", str(ctx.exception))

    def test_create_workspace_from_starter_rejects_invalid_names(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        invalid_names = (
            "",
            "   ",
            ".",
            "..",
            "../escape",
            "escape/../outside",
            "nested/path",
            "nested\\path",
            "/absolute",
            "./relative",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            for invalid_name in invalid_names:
                with self.subTest(invalid_name=invalid_name):
                    with self.assertRaises(ValueError) as ctx:
                        create_workspace_from_starter(invalid_name, root=root)
                    self.assertIn("invalid workspace name", str(ctx.exception))
                    self.assertNotIn("already exists", str(ctx.exception))

    def test_list_workspaces_skips_corrupted_workspace_metadata(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter, list_workspaces
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            healthy = create_workspace_from_starter("billing-intake", root=root)
            corrupted = create_workspace_from_starter("ops-rollout", root=root)
            corrupted.metadata_path.write_text("{not-json", encoding="utf-8")

            listed = list_workspaces(root=root)

        self.assertEqual([item.name for item in listed], [healthy.name])

    def test_get_workspace_rejects_corrupted_workspace_metadata(self):
        try:
            from traceloom.workspaces import create_workspace_from_starter, get_workspace
        except ImportError as exc:
            self.fail(f"could not import workspace helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = create_workspace_from_starter("billing-intake", root=root)
            payload = json.loads(workspace.metadata_path.read_text(encoding="utf-8"))
            payload.pop("active_repository_path")
            workspace.metadata_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                get_workspace("billing-intake", root=root)

        self.assertIn("invalid workspace metadata", str(ctx.exception))

    def test_created_workspace_from_starter_is_schema_valid(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
            from traceloom.repository import load_repository
            from traceloom.validators import load_schema, validate_repository
            from traceloom.workspaces import create_workspace_from_starter
        except ImportError as exc:
            self.fail(f"could not import workspace validation helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_workspace_from_starter("billing-intake", root=temp_dir)
            schema = load_schema(resolve_default_schema_path(module_file=__file__))
            issues = validate_repository(load_repository([workspace.active_repository_path]), schema)

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
