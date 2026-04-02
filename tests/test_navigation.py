from copy import deepcopy
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


def _import_runtime():
    try:
        from traceloom.navigation import get_delivery_slice_navigation
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema
    except ImportError as exc:
        pytest.fail(f"could not import navigation runtime: {exc}")
    return get_delivery_slice_navigation, load_repository, load_schema


def _load_example_context():
    get_delivery_slice_navigation, load_repository, load_schema = _import_runtime()
    repository = load_repository([EXAMPLE_DIR])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, get_delivery_slice_navigation


def _load_versioned_example_context():
    get_delivery_slice_navigation, load_repository, load_schema = _import_runtime()
    repository = load_repository([VERSIONED_EXAMPLE_DIR])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, get_delivery_slice_navigation


def test_get_delivery_slice_navigation_returns_pm_kickoff_for_unknown_feature_key():
    repository, schema, get_delivery_slice_navigation = _load_example_context()

    payload = get_delivery_slice_navigation(repository, schema, "brand-new-import")

    assert payload["feature_key"] == "brand-new-import"
    assert payload["slice_stage"] == "brief_missing"
    assert payload["next_recommended_capability"] == "pm"
    assert payload["next_recommended_artifact_type"] == "brief"
    assert payload["next_recommended_actions"][0]["action_type"] == "create_artifact_draft"


def test_get_delivery_slice_navigation_uses_v0_2_baselines_in_versioned_repo():
    repository, schema, get_delivery_slice_navigation = _load_versioned_example_context()

    payload = get_delivery_slice_navigation(repository, schema, "user-tag-bulk-import")

    assert payload["artifacts"]["brief"]["artifact_id"] == "BRIEF-2026-002"
    assert payload["artifacts"]["prd_story_pack"]["artifact_id"] == "PRD-2026-002"
    assert payload["artifacts"]["solution_design"]["artifact_id"] == "DESIGN-2026-002"
    assert payload["slice_stage"] == "brief_in_progress"


def test_get_delivery_slice_navigation_clamps_example_repo_at_design_handoff_ready():
    repository, schema, get_delivery_slice_navigation = _load_example_context()

    payload = get_delivery_slice_navigation(repository, schema, "user-tag-bulk-import")

    assert payload["slice_stage"] == "design_handoff_ready"
    assert payload["current_focus"]["artifact_id"] == "DESIGN-2026-001"
    assert payload["handoff_readiness"]["ready"] is True
    assert payload["upcoming_handoff"] == {"from_stage": "design", "to_stage": "execution"}


def test_get_delivery_slice_navigation_switches_to_tech_lead_at_prd_handoff():
    repository, schema, get_delivery_slice_navigation = _load_example_context()
    repository.artifacts_by_id = deepcopy(repository.artifacts_by_id)
    repository.trace_units_by_id = deepcopy(repository.trace_units_by_id)
    repository.relation_edges_by_id = deepcopy(repository.relation_edges_by_id)

    design_artifact = repository.artifacts_by_id.pop("DESIGN-2026-001")
    repository.artifacts_by_id["PRD-2026-001"].header = deepcopy(repository.artifacts_by_id["PRD-2026-001"].header)
    repository.artifacts_by_id["PRD-2026-001"].header["status"] = "in_review"
    repository.artifacts_by_id["PRD-2026-001"].header["downstream_refs"] = []
    repository.artifacts_by_id["PRD-2026-001"].header["status_history"] = []
    for unit in design_artifact.trace_units:
        repository.trace_units_by_id.pop(unit["id"], None)
    for edge in design_artifact.relation_edges:
        repository.relation_edges_by_id.pop(edge["edge_id"], None)

    payload = get_delivery_slice_navigation(repository, schema, "user-tag-bulk-import")

    assert payload["slice_stage"] == "prd_handoff_ready"
    assert payload["current_focus"]["artifact_id"] == "PRD-2026-001"
    assert payload["next_recommended_capability"] == "tech_lead"
    assert payload["next_recommended_artifact_type"] == "solution_design"
    assert payload["next_recommended_actions"][0]["action_type"] == "create_artifact_draft"


def test_get_delivery_slice_navigation_surfaces_workflow_blockers_in_handoff_readiness():
    repository, schema, get_delivery_slice_navigation = _load_versioned_example_context()

    payload = get_delivery_slice_navigation(repository, schema, "user-tag-bulk-import")

    assert payload["slice_stage"] == "brief_in_progress"
    assert any(item["kind"] == "missing_approval_capability" and item["capability"] == "pm" for item in payload["blocking_items"])
    assert payload["handoff_readiness"] == {
        "ready": False,
        "target_stage": "prd",
        "missing_conditions": ["brief_gate_approved_or_waived"],
    }
