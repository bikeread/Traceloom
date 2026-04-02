from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "README.zh-CN.md",
    REPO_ROOT / "docs" / "guide" / "en" / "getting-started.md",
    REPO_ROOT / "docs" / "guide" / "zh-CN" / "getting-started.md",
]
CLI_GUIDES = [
    REPO_ROOT / "docs" / "guide" / "en" / "cli.md",
    REPO_ROOT / "docs" / "guide" / "zh-CN" / "cli.md",
]
MCP_GUIDES = [
    REPO_ROOT / "docs" / "guide" / "en" / "mcp.md",
    REPO_ROOT / "docs" / "guide" / "zh-CN" / "mcp.md",
]


def test_public_docs_surface_centers_runtime_and_first_closed_loop():
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")

        for expected_snippet in (
            "Git-native artifact runtime",
            "current requirement",
            "Brief",
            "PRD",
            "Solution Design",
            "design-check",
        ):
            assert expected_snippet in text, f"{path}: {expected_snippet}"


def test_public_docs_surface_mentions_minimal_requirement_template():
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")
        assert "templates/minimal-requirement-repo" in text, path


def test_public_docs_surface_drops_old_path_selector_story():
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")

        for hidden_snippet in (
            "Path 1: Evaluate Traceloom",
            "Path 2: Start a Real Requirement",
        ):
            assert hidden_snippet not in text, f"{path}: {hidden_snippet}"


def test_cli_guides_group_core_runtime_local_writes_and_advanced_workflows():
    for path in CLI_GUIDES:
        text = path.read_text(encoding="utf-8")

        for expected_snippet in (
            "Core runtime",
            "design-check",
            "navigate-feature",
            "Local governed write commands",
            "Advanced local workflows",
            "workspace create",
            "bootstrap prepare",
        ):
            assert expected_snippet in text, f"{path}: {expected_snippet}"


def test_mcp_guides_document_design_check_and_read_only_boundary():
    for path in MCP_GUIDES:
        text = path.read_text(encoding="utf-8")

        for expected_snippet in (
            "read-only",
            "get_delivery_slice_navigation",
            "check_design_completeness",
            "design-check",
        ):
            assert expected_snippet in text, f"{path}: {expected_snippet}"


def test_cherry_guides_still_document_companion_demo_startup():
    for path in (
        REPO_ROOT / "docs" / "guide" / "en" / "cherry-studio.md",
        REPO_ROOT / "docs" / "guide" / "zh-CN" / "cherry-studio.md",
    ):
        text = path.read_text(encoding="utf-8")

        for expected_snippet in (
            "companion executable",
            "mcp --demo",
        ):
            assert expected_snippet in text, f"{path}: {expected_snippet}"


def test_ci_workflow_smokes_installed_traceloom_console_script():
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "validate-artifacts.yml"
    ).read_text(encoding="utf-8")

    for expected_snippet in (
        "python -m pip install .",
        "traceloom --help",
        "traceloom validate examples/user-tag-bulk-import",
        "traceloom mcp --paths examples/user-tag-bulk-import --print-tools",
    ):
        assert expected_snippet in workflow_text, expected_snippet


def test_companion_build_workflow_targets_macos_and_windows():
    workflow_text = (
        REPO_ROOT / ".github" / "workflows" / "build-companion-executable.yml"
    ).read_text(encoding="utf-8")

    for expected_snippet in (
        "macos-latest",
        "windows-latest",
        "pyinstaller pyinstaller/traceloom.spec",
        "python scripts/smoke_companion_bundle.py",
    ):
        assert expected_snippet in workflow_text, expected_snippet
