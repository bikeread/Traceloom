from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.git_fixture_helpers import init_git_example_repo


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


def _import_runtime():
    try:
        from traceloom.design_checks import check_design_completeness
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema
    except ImportError as exc:
        pytest.fail(f"could not import design check runtime: {exc}")
    return check_design_completeness, load_repository, load_schema


def _import_fixture_tools():
    try:
        from traceloom.artifact_io import replace_relation_edges_block, write_artifact_document
        from traceloom.parser import parse_artifact
    except ImportError as exc:
        pytest.fail(f"could not import fixture tools: {exc}")
    return replace_relation_edges_block, write_artifact_document, parse_artifact


def _load_context(root: Path):
    check_design_completeness, load_repository, load_schema = _import_runtime()
    repository = load_repository([root])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, check_design_completeness


@contextmanager
def _git_fixture():
    temp_dir, fixture_root = init_git_example_repo(EXAMPLE_DIR)
    try:
        yield fixture_root
    finally:
        temp_dir.cleanup()


def _remove_requirement_coverage_edge(path: Path, edge_id: str) -> None:
    replace_relation_edges_block, write_artifact_document, parse_artifact = _import_fixture_tools()
    artifact = parse_artifact(path)
    remaining_edges = [edge for edge in artifact.relation_edges if edge.get("edge_id") != edge_id]
    body = replace_relation_edges_block(artifact.body, remaining_edges)
    write_artifact_document(path, artifact.header, body)


def test_check_design_completeness_returns_ready_payload_for_example_repo():
    repository, schema, check_design_completeness = _load_context(EXAMPLE_DIR)

    payload = check_design_completeness(repository, schema, feature_key="user-tag-bulk-import")

    assert payload["feature_key"] == "user-tag-bulk-import"
    assert payload["design_artifact_id"] == "DESIGN-2026-001"
    assert payload["ready"] is True
    assert payload["blocker_count"] == 0
    assert payload["blocking_items"] == []


def test_check_design_completeness_flags_missing_design_artifact():
    with _git_fixture() as fixture_root:
        (fixture_root / "03_solution_design.md").unlink()
        repository, schema, check_design_completeness = _load_context(fixture_root)

        payload = check_design_completeness(repository, schema, feature_key="user-tag-bulk-import")

    assert payload["ready"] is False
    assert payload["design_artifact_id"] is None
    assert any(item["kind"] == "missing_design_artifact" for item in payload["blocking_items"])
    assert any(item["action_type"] == "create_artifact_draft" for item in payload["recommendations"])


def test_check_design_completeness_flags_missing_requirement_coverage():
    with _git_fixture() as fixture_root:
        _remove_requirement_coverage_edge(fixture_root / "03_solution_design.md", "EDGE-0003")
        repository, schema, check_design_completeness = _load_context(fixture_root)

        payload = check_design_completeness(repository, schema, feature_key="user-tag-bulk-import")

    assert payload["ready"] is False
    assert any(
        item["kind"] == "missing_requirement_coverage" and item["upstream_unit_id"] == "REQ-001"
        for item in payload["blocking_items"]
    )
    assert any(item["action_type"] == "revise_artifact_draft" for item in payload["recommendations"])
