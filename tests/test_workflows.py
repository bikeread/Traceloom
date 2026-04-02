from copy import deepcopy
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


def _import_runtime():
    try:
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema
        from traceloom.workflows import evaluate_artifact_workflow, list_default_gate_policies
    except ImportError as exc:
        pytest.fail(f"could not import workflow runtime: {exc}")
    return load_repository, load_schema, evaluate_artifact_workflow, list_default_gate_policies


def _load_example_context():
    load_repository, load_schema, evaluate_artifact_workflow, list_default_gate_policies = _import_runtime()
    repository = load_repository([EXAMPLE_DIR])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, evaluate_artifact_workflow, list_default_gate_policies


def _load_versioned_example_context():
    load_repository, load_schema, evaluate_artifact_workflow, list_default_gate_policies = _import_runtime()
    repository = load_repository([VERSIONED_EXAMPLE_DIR])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, evaluate_artifact_workflow, list_default_gate_policies


def test_list_default_gate_policies_returns_canonical_track_b_order():
    _, _, _, list_default_gate_policies = _load_example_context()

    policies = list_default_gate_policies()

    assert [policy["gate_id"] for policy in policies] == [
        "brief_gate",
        "prd_gate",
        "design_gate",
        "execution_readiness_gate",
        "test_case_gate",
        "release_review_gate",
    ]
    assert [policy["artifact_type"] for policy in policies] == [
        "brief",
        "prd_story_pack",
        "solution_design",
        "execution_plan",
        "test_acceptance",
        "release_review",
    ]


def test_evaluate_artifact_workflow_returns_prd_gate_result_for_example():
    repository, schema, evaluate_artifact_workflow, _ = _load_example_context()

    payload = evaluate_artifact_workflow(repository, schema, "PRD-2026-001")

    assert payload["artifact_id"] == "PRD-2026-001"
    assert payload["gate_id"] == "prd_gate"
    assert payload["delivery_stage"] == "prd"
    assert payload["current_outcome"] == "approved"
    assert payload["required_approval_capabilities"] == ["tech_lead", "qa"]
    assert payload["missing_approval_capabilities"] == []
    assert payload["missing_evidence"] == []
    assert payload["controls_transition"] == {"from_status": "in_review", "to_status": "approved"}
    assert payload["controlled_transition_allowed"] is True


def test_evaluate_artifact_workflow_accepts_matching_capability_when_role_differs():
    repository, schema, evaluate_artifact_workflow, _ = _load_example_context()

    artifact = repository.artifacts_by_id["PRD-2026-001"]
    artifact.header["review_records"] = deepcopy(artifact.header["review_records"])
    artifact.header["review_records"][1]["reviewer"]["role"] = "release_owner"
    artifact.header["review_records"][1]["reviewer"]["capability"] = "qa"

    payload = evaluate_artifact_workflow(repository, schema, "PRD-2026-001")

    assert payload["current_outcome"] == "approved"
    assert payload["satisfied_approval_capabilities"] == ["qa", "tech_lead"]
    assert payload["missing_approval_capabilities"] == []


def test_evaluate_artifact_workflow_blocks_design_gate_when_prd_gate_has_changes_requested():
    repository, schema, evaluate_artifact_workflow, _ = _load_example_context()

    artifact = repository.artifacts_by_id["PRD-2026-001"]
    artifact.header["review_records"] = deepcopy(artifact.header["review_records"])
    artifact.header["review_records"][0]["decision"] = "changes_requested"
    artifact.header["review_records"][0]["related_transition"] = "in_review->draft"

    payload = evaluate_artifact_workflow(repository, schema, "DESIGN-2026-001")

    assert payload["current_outcome"] == "blocked"
    assert payload["controlled_transition_allowed"] is False
    assert payload["depends_on"] == [{"gate_id": "prd_gate", "outcome": "changes_requested"}]
    assert any(
        reason["kind"] == "unsatisfied_dependency" and reason["gate_id"] == "prd_gate"
        for reason in payload["blocking_reasons"]
    )


def test_evaluate_artifact_workflow_blocks_design_gate_when_open_question_exists():
    repository, schema, evaluate_artifact_workflow, _ = _load_example_context()

    repository.artifacts_by_id["DESIGN-2026-001"].header["open_questions"] = [
        {"q_id": "Q-101", "status": "open", "note": "Need explicit rollback guidance."}
    ]

    payload = evaluate_artifact_workflow(repository, schema, "DESIGN-2026-001")

    assert payload["current_outcome"] == "blocked"
    assert payload["controlled_transition_allowed"] is False
    assert any(
        reason["kind"] == "open_question" and reason["q_id"] == "Q-101"
        for reason in payload["blocking_reasons"]
    )


def test_evaluate_artifact_workflow_blocks_prd_gate_when_scoped_validation_issue_exists():
    repository, schema, evaluate_artifact_workflow, _ = _load_example_context()

    repository.relation_edges_by_id.pop("EDGE-0002")

    payload = evaluate_artifact_workflow(repository, schema, "PRD-2026-001")

    assert payload["current_outcome"] == "blocked"
    assert payload["controlled_transition_allowed"] is False
    assert any(
        reason["kind"] == "validation_issue" and reason["code"] == "missing_traceability"
        for reason in payload["blocking_reasons"]
    )


def test_evaluate_artifact_workflow_uses_current_artifact_version_in_versioned_repo():
    repository, schema, evaluate_artifact_workflow, _ = _load_versioned_example_context()

    payload = evaluate_artifact_workflow(repository, schema, "PRD-2026-002")

    assert payload["artifact_id"] == "PRD-2026-002"
    assert payload["artifact_version"] == "v0.2"
    assert payload["gate_id"] == "prd_gate"
    assert payload["current_outcome"] == "blocked"
    assert payload["controlled_transition_allowed"] is False
