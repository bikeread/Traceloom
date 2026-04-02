from pathlib import Path
import tempfile
import unittest


class BundledAssetTests(unittest.TestCase):
    def test_resolve_bundled_demo_root_contains_canonical_demo_files(self):
        try:
            from traceloom.bundled_assets import resolve_bundled_demo_root
        except ImportError as exc:
            self.fail(f"could not import bundled asset helpers: {exc}")

        demo_root = resolve_bundled_demo_root()

        for relative_path in (
            "01_brief.md",
            "02_prd.md",
            "03_solution_design.md",
            "04_execution_plan.md",
            "05_test_acceptance.md",
            "06_release_review.md",
            "README.md",
        ):
            self.assertTrue((demo_root / relative_path).is_file(), relative_path)

    def test_materialize_bundled_demo_repo_copies_expected_artifacts(self):
        try:
            from traceloom.bundled_assets import materialize_bundled_demo_repo
        except ImportError as exc:
            self.fail(f"could not import bundled asset helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "demo"
            materialized = materialize_bundled_demo_repo(target)

            self.assertEqual(materialized, target)

            for relative_path in (
                "01_brief.md",
                "02_prd.md",
                "03_solution_design.md",
                "04_execution_plan.md",
                "05_test_acceptance.md",
                "06_release_review.md",
                "README.md",
            ):
                self.assertTrue((target / relative_path).is_file(), relative_path)

    def test_make_brief_handoff_ready_keeps_guided_promotion_smoke_path_valid(self):
        try:
            from scripts.smoke_companion_bundle import make_brief_handoff_ready
            from traceloom.bundled_assets import materialize_bundled_demo_repo
            from traceloom.defaults import resolve_default_schema_path
            from traceloom.guided_actions import execute_guided_action_package, prepare_guided_action_package
            from traceloom.repository import load_repository
            from traceloom.validators import load_schema, validate_repository
        except ImportError as exc:
            self.fail(f"could not import smoke helpers: {exc}")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = materialize_bundled_demo_repo(Path(temp_dir) / "demo")
            make_brief_handoff_ready(repo_root)

            repository = load_repository([repo_root])
            schema = load_schema(resolve_default_schema_path(module_file=__file__))
            issues = validate_repository(repository, schema)

            self.assertEqual([], issues)

            package = prepare_guided_action_package(
                repository,
                schema,
                feature_key="user-tag-bulk-import",
                request={
                    "action_type": "promote_artifact_status",
                    "target_status": "approved",
                    "governance_payload": {
                        "actor_id": "user:li.pm",
                        "role": "pm",
                        "capability": "artifact_governance",
                        "decision_authority": "brief_owner",
                        "changed_at": "2026-03-26T12:10:00+08:00",
                    },
                },
            )
            result = execute_guided_action_package(repo_root, package=package)

            self.assertTrue(result["accepted"])


if __name__ == "__main__":
    unittest.main()
