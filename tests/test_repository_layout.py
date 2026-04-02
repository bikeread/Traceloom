from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_DESIGN_DOCS = [
    "00_executive_summary.md",
    "01_product_definition.md",
    "02_scope_and_boundaries.md",
    "03_ai_traceable_artifact_map_v1.md",
    "05_design_principles_and_constraints.md",
    "06_trellis_positioning.md",
    "07_next_steps_for_codex.md",
    "08_mvp_implementation_suggestions.md",
    "09_runtime_roadmap.md",
    "10_product_shape_recommendation.md",
    "handoff_index.json",
]
GUIDE_DOCS = [
    "getting-started.md",
    "cherry-studio.md",
    "examples.md",
    "compatibility.md",
    "adoption.md",
    "cli.md",
    "mcp.md",
    "schema.md",
    "roadmap.md",
]
PLAYBOOK_DOCS = [
    "pm.md",
    "engineering.md",
    "qa.md",
    "reviewer.md",
]
GOVERNANCE_DOCS = [
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "CHANGELOG.md",
]
STARTER_TEMPLATE_FILES = [
    "README.md",
    "01_brief.md",
    "02_prd.md",
    "03_solution_design.md",
    "04_execution_plan.md",
    "05_test_acceptance.md",
    "06_release_review.md",
]
MINIMAL_TEMPLATE_FILES = [
    "README.md",
    "01_brief.md",
]


def test_root_surface_keeps_design_docs_out_of_the_project_entrypoint():
    for relative_path in ROOT_DESIGN_DOCS:
        assert not (REPO_ROOT / relative_path).exists(), relative_path

    assert (REPO_ROOT / "04_schema_v1.yaml").is_file()


def test_docs_layers_exist_with_expected_public_and_design_materials():
    guide_dir = REPO_ROOT / "docs" / "guide"
    english_guide_dir = guide_dir / "en"
    chinese_guide_dir = guide_dir / "zh-CN"

    assert guide_dir.is_dir()
    assert english_guide_dir.is_dir()
    assert chinese_guide_dir.is_dir()

    for relative_path in GUIDE_DOCS:
        assert (english_guide_dir / relative_path).is_file(), relative_path
        assert (chinese_guide_dir / relative_path).is_file(), relative_path


def test_root_surface_includes_open_source_governance_files():
    for relative_path in GOVERNANCE_DOCS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_pyproject_exposes_public_package_metadata():
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    for expected_snippet in (
        "license = {text = \"MIT\"}",
        "authors = [",
        "name = \"bikeread\"",
        "email = \"bikeread2008@gmail.com\"",
        "urls = {",
        "Homepage = \"https://github.com/bikeread/Traceloom\"",
        "Repository = \"https://github.com/bikeread/Traceloom\"",
        "Issues = \"https://github.com/bikeread/Traceloom/issues\"",
        "classifiers = [",
        "\"License :: OSI Approved :: MIT License\"",
        "\"Development Status :: 4 - Beta\"",
        "\"Topic :: Software Development :: Quality Assurance\"",
        "keywords = [",
        "\"mcp\"",
        "\"traceability\"",
        "\"ai\"",
    ):
        assert expected_snippet in pyproject_text, expected_snippet


def test_readme_points_to_docs_layers_instead_of_root_level_design_docs():
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for relative_path in (
        "docs/guide/en/getting-started.md",
        "docs/guide/en/examples.md",
        "docs/guide/en/cli.md",
        "docs/guide/en/mcp.md",
        "docs/guide/en/schema.md",
        "docs/guide/en/roadmap.md",
    ):
        assert relative_path in readme_text, relative_path

    for relative_path in (
        "docs/design/",
        "docs/design/00_executive_summary.md",
        "docs/design/09_runtime_roadmap.md",
        "(00_executive_summary.md)",
        "(01_product_definition.md)",
        "(02_scope_and_boundaries.md)",
        "(03_ai_traceable_artifact_map_v1.md)",
        "(05_design_principles_and_constraints.md)",
        "(06_trellis_positioning.md)",
        "(07_next_steps_for_codex.md)",
        "(08_mvp_implementation_suggestions.md)",
        "(09_runtime_roadmap.md)",
        "(10_product_shape_recommendation.md)",
        "(handoff_index.json)",
    ):
        assert relative_path not in readme_text, relative_path


def test_public_playbooks_exist_in_both_languages():
    english_dir = REPO_ROOT / "docs" / "guide" / "en" / "playbooks"
    chinese_dir = REPO_ROOT / "docs" / "guide" / "zh-CN" / "playbooks"

    assert english_dir.is_dir()
    assert chinese_dir.is_dir()

    for relative_path in PLAYBOOK_DOCS:
        assert (english_dir / relative_path).is_file(), relative_path
        assert (chinese_dir / relative_path).is_file(), relative_path


def test_starter_repo_template_exposes_canonical_six_artifact_files():
    template_dir = REPO_ROOT / "templates" / "starter-repo"

    assert template_dir.is_dir()

    for relative_path in STARTER_TEMPLATE_FILES:
        assert (template_dir / relative_path).is_file(), relative_path


def test_minimal_requirement_template_exposes_brief_only_files():
    template_dir = REPO_ROOT / "templates" / "minimal-requirement-repo"

    assert template_dir.is_dir()

    for relative_path in MINIMAL_TEMPLATE_FILES:
        assert (template_dir / relative_path).is_file(), relative_path


def test_companion_packaging_assets_surface_exists():
    for relative_path in (
        REPO_ROOT / "traceloom" / "resources" / "04_schema_v1.yaml",
        REPO_ROOT / "traceloom" / "bundled" / "demo-repo" / "01_brief.md",
        REPO_ROOT / "traceloom" / "bundled" / "demo-repo" / "06_release_review.md",
        REPO_ROOT / "scripts" / "sync_bundled_assets.py",
    ):
        assert relative_path.is_file(), relative_path


def test_requirement_bootstrap_phase1_runtime_surface_exists():
    for relative_path in (
        REPO_ROOT / "traceloom" / "workspaces.py",
        REPO_ROOT / "traceloom" / "bootstrap.py",
    ):
        assert relative_path.is_file(), relative_path


def test_companion_build_surface_exists():
    for relative_path in (
        REPO_ROOT / "pyinstaller" / "traceloom.spec",
        REPO_ROOT / "scripts" / "smoke_companion_bundle.py",
        REPO_ROOT / ".github" / "workflows" / "build-companion-executable.yml",
    ):
        assert relative_path.is_file(), relative_path


def test_companion_build_workflow_uploads_platform_artifacts():
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "build-companion-executable.yml"
    ).read_text(encoding="utf-8")

    for expected_snippet in (
        "actions/upload-artifact",
        "traceloom-companion-macos",
        "traceloom-companion-windows",
        "path: dist/traceloom",
    ):
        assert expected_snippet in workflow_text, expected_snippet


def test_pyinstaller_spec_executes_with_pyinstaller_namespace():
    spec_path = REPO_ROOT / "pyinstaller" / "traceloom.spec"
    spec_text = spec_path.read_text(encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_analysis(scripts, **kwargs):
        captured["scripts"] = scripts
        captured["datas"] = kwargs["datas"]
        captured["hiddenimports"] = kwargs["hiddenimports"]
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[])

    def fake_exe(*args, **kwargs):
        captured["exe_kwargs"] = kwargs
        return SimpleNamespace()

    namespace = {
        "SPEC": str(spec_path),
        "SPECPATH": str(spec_path.parent),
        "specnm": "traceloom",
        "DISTPATH": str(REPO_ROOT / "dist"),
        "HOMEPATH": str(REPO_ROOT),
        "WARNFILE": str(REPO_ROOT / "build" / "warn-traceloom.txt"),
        "workpath": str(REPO_ROOT / "build"),
        "Analysis": fake_analysis,
        "PYZ": lambda pure: pure,
        "EXE": fake_exe,
        "COLLECT": lambda *args, **kwargs: SimpleNamespace(),
    }

    exec(compile(spec_text, str(spec_path), "exec"), namespace, namespace)

    assert captured["scripts"] == [str(REPO_ROOT / "traceloom" / "__main__.py")]
    assert (str(REPO_ROOT / "traceloom" / "bundled"), "traceloom/bundled") in captured["datas"]
    assert (str(REPO_ROOT / "traceloom" / "resources"), "traceloom/resources") in captured["datas"]
    assert captured["exe_kwargs"]["exclude_binaries"] is True
    for hiddenimport in (
        "pkg_resources._vendor.appdirs",
        "pkg_resources._vendor.packaging",
        "pkg_resources._vendor.pyparsing",
    ):
        assert hiddenimport in captured["hiddenimports"]


def test_readme_front_door_centers_runtime_and_first_closed_loop():
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for expected_snippet in (
        "Git-native artifact runtime",
        "current requirement",
        "Brief",
        "PRD",
        "Solution Design",
        "design-check",
        "Advanced setup",
        "docs/guide/en/getting-started.md",
        "docs/guide/en/cli.md",
    ):
        assert expected_snippet in readme_text, expected_snippet

    assert "Path 1: Evaluate Traceloom" not in readme_text
    assert "Path 2: Start a Real Requirement" not in readme_text

    front_door_text = readme_text.split("Advanced setup", 1)[0]
    assert "Core runtime" not in front_door_text


def test_getting_started_front_door_centers_first_closed_loop():
    guide_text = (REPO_ROOT / "docs" / "guide" / "en" / "getting-started.md").read_text(encoding="utf-8")

    for expected_snippet in (
        "Git-native artifact runtime",
        "current requirement",
        "Brief",
        "PRD",
        "Solution Design",
        "design-check",
        "templates/minimal-requirement-repo",
        "Advanced setup",
        "cli.md",
    ):
        assert expected_snippet in guide_text, expected_snippet

    assert "Path 1: Evaluate Traceloom" not in guide_text
    assert "Path 2: Start a Real Requirement" not in guide_text


def test_cherry_studio_guide_points_back_to_public_entry_guides():
    for relative_path in (
        REPO_ROOT / "docs" / "guide" / "en" / "cherry-studio.md",
        REPO_ROOT / "docs" / "guide" / "zh-CN" / "cherry-studio.md",
    ):
        guide_text = relative_path.read_text(encoding="utf-8")

        for expected_snippet in (
            "getting-started.md",
            "mcp.md",
        ):
            assert expected_snippet in guide_text, f"{relative_path}: {expected_snippet}"


def test_compatibility_guides_call_out_cli_first_supported_outsider_path():
    english_text = (
        REPO_ROOT / "docs" / "guide" / "en" / "compatibility.md"
    ).read_text(encoding="utf-8")
    chinese_text = (
        REPO_ROOT / "docs" / "guide" / "zh-CN" / "compatibility.md"
    ).read_text(encoding="utf-8")

    for expected_snippet in (
        "installed `traceloom` CLI",
        "primary outsider path",
        "python -m traceloom",
        "fallback-only",
    ):
        assert expected_snippet in english_text, expected_snippet

    for expected_snippet in (
        "已安装的 `traceloom` CLI",
        "主要 outsider 路径",
        "python -m traceloom",
        "仅作为 fallback",
    ):
        assert expected_snippet in chinese_text, expected_snippet


def test_mcp_guide_points_to_cherry_studio_as_first_client():
    guide_text = (REPO_ROOT / "docs" / "guide" / "en" / "mcp.md").read_text(encoding="utf-8")

    for expected_snippet in (
        "Cherry Studio",
        "first official recommended client",
        "cherry-studio.md",
    ):
        assert expected_snippet in guide_text, expected_snippet


def test_cli_and_mcp_guides_surface_navigation_and_design_check_entrypoints():
    for relative_path in (
        REPO_ROOT / "docs" / "guide" / "en" / "cli.md",
        REPO_ROOT / "docs" / "guide" / "zh-CN" / "cli.md",
        REPO_ROOT / "docs" / "guide" / "en" / "mcp.md",
        REPO_ROOT / "docs" / "guide" / "zh-CN" / "mcp.md",
    ):
        guide_text = relative_path.read_text(encoding="utf-8")

        for expected_snippet in (
            "navigate-feature",
            "get_delivery_slice_navigation",
            "design-check",
            "check_design_completeness",
            "read-only",
        ):
            assert expected_snippet in guide_text, f"{relative_path}: {expected_snippet}"


def test_guided_action_runtime_docs_and_changelog_surface_local_read_only_execution():
    guide_text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    for expected_snippet in (
        "guided_action_package",
        "prepare-guided-action",
        "execute-guided-action",
        "read-only",
    ):
        assert expected_snippet in guide_text, expected_snippet


def test_root_readmes_offer_bilingual_entrypoints():
    english_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    chinese_path = REPO_ROOT / "README.zh-CN.md"

    assert chinese_path.is_file()
    assert "README.zh-CN.md" in english_readme

    chinese_readme = chinese_path.read_text(encoding="utf-8")
    assert "README.md" in chinese_readme


def test_guide_docs_offer_bilingual_entrypoints():
    english_guide_dir = REPO_ROOT / "docs" / "guide" / "en"
    chinese_guide_dir = REPO_ROOT / "docs" / "guide" / "zh-CN"

    assert english_guide_dir.is_dir()
    assert chinese_guide_dir.is_dir()

    for relative_path in GUIDE_DOCS:
        english_path = english_guide_dir / relative_path
        chinese_path = chinese_guide_dir / relative_path

        assert english_path.is_file(), relative_path
        assert chinese_path.is_file(), relative_path

        english_text = english_path.read_text(encoding="utf-8")
        chinese_text = chinese_path.read_text(encoding="utf-8")

        assert f"../zh-CN/{relative_path}" in english_text, relative_path
        assert f"../en/{relative_path}" in chinese_text, relative_path
