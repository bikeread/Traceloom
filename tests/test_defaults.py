from pathlib import Path
import tempfile
import unittest


class DefaultPathTests(unittest.TestCase):
    def test_resolve_default_schema_path_prefers_cwd_schema_for_installed_layout(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            schema_path = root / "04_schema_v1.yaml"
            schema_path.write_text("version: test\n", encoding="utf-8")
            fake_module_file = root / "venv" / "lib" / "python3.10" / "site-packages" / "traceloom" / "cli.py"
            fake_module_file.parent.mkdir(parents=True, exist_ok=True)
            fake_module_file.write_text("# fake", encoding="utf-8")

            resolved = resolve_default_schema_path(cwd=root, module_file=fake_module_file)

        self.assertEqual(resolved, schema_path)

    def test_resolve_default_schema_path_falls_back_to_repo_relative_schema(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = root / "repo"
            schema_path = repo_root / "04_schema_v1.yaml"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text("version: test\n", encoding="utf-8")
            module_file = repo_root / "traceloom" / "cli.py"
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text("# fake", encoding="utf-8")

            resolved = resolve_default_schema_path(cwd=root, module_file=module_file)

        self.assertEqual(resolved, schema_path)

    def test_resolve_default_schema_path_falls_back_to_packaged_schema_in_installed_layout(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            installed_package_dir = root / "venv" / "lib" / "python3.10" / "site-packages" / "traceloom"
            packaged_schema_path = installed_package_dir / "resources" / "04_schema_v1.yaml"
            packaged_schema_path.parent.mkdir(parents=True, exist_ok=True)
            packaged_schema_path.write_text("version: packaged-test\n", encoding="utf-8")
            module_file = installed_package_dir / "defaults.py"
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text("# fake", encoding="utf-8")
            cwd_without_schema = root / "workspace"
            cwd_without_schema.mkdir(parents=True, exist_ok=True)

            resolved = resolve_default_schema_path(cwd=cwd_without_schema, module_file=module_file)

        self.assertEqual(resolved, packaged_schema_path)

    def test_resolve_default_schema_path_ignores_directory_named_like_schema_in_cwd(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "04_schema_v1.yaml").mkdir()
            repo_root = root / "repo"
            schema_path = repo_root / "04_schema_v1.yaml"
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text("version: repo-test\n", encoding="utf-8")
            module_file = repo_root / "traceloom" / "cli.py"
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text("# fake", encoding="utf-8")

            resolved = resolve_default_schema_path(cwd=root, module_file=module_file)

        self.assertEqual(resolved, schema_path)

    def test_resolve_default_schema_path_ignores_packaged_directory_named_like_schema(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            installed_package_dir = root / "venv" / "lib" / "python3.10" / "site-packages" / "traceloom"
            packaged_directory = installed_package_dir / "resources" / "04_schema_v1.yaml"
            packaged_directory.mkdir(parents=True, exist_ok=True)
            module_file = installed_package_dir / "defaults.py"
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text("# fake", encoding="utf-8")

            resolved = resolve_default_schema_path(cwd=root / "workspace", module_file=module_file)

        self.assertNotEqual(resolved, packaged_directory)
        self.assertEqual(resolved, installed_package_dir.parent / "04_schema_v1.yaml")

    def test_resolve_default_schema_path_rejects_repo_relative_directory_named_like_schema(self):
        try:
            from traceloom.defaults import resolve_default_schema_path
        except ImportError as exc:
            self.fail(f"could not import defaults helper: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_root = root / "repo"
            repo_candidate = repo_root / "04_schema_v1.yaml"
            repo_candidate.mkdir(parents=True, exist_ok=True)
            module_file = repo_root / "traceloom" / "cli.py"
            module_file.parent.mkdir(parents=True, exist_ok=True)
            module_file.write_text("# fake", encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                resolve_default_schema_path(cwd=root / "workspace", module_file=module_file)

        self.assertIn("not a file", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
