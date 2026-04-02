from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from tests.git_fixture_helpers import init_git_example_repo


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"
SCHEMA_PATH = REPO_ROOT / "04_schema_v1.yaml"


def _import_guided_action_runtime():
    try:
        from traceloom.guided_actions import prepare_guided_action_package
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema
    except ImportError as exc:
        pytest.fail(f"could not import guided action runtime: {exc}")
    return prepare_guided_action_package, load_repository, load_schema


def _import_fixture_tools():
    try:
        from traceloom.artifact_io import write_artifact_header
        from traceloom.parser import parse_artifact
    except ImportError as exc:
        pytest.fail(f"could not import fixture tools: {exc}")
    return write_artifact_header, parse_artifact


def _import_guided_action_executor():
    try:
        from traceloom.guided_actions import execute_guided_action_package
    except ImportError as exc:
        pytest.fail(f"could not import guided action executor: {exc}")
    return execute_guided_action_package


def _import_workspace_bootstrap_runtime():
    try:
        from traceloom.bootstrap import apply_bootstrap_seed_to_workspace
        from traceloom.workspaces import create_workspace_from_starter
    except ImportError as exc:
        pytest.fail(f"could not import workspace bootstrap runtime: {exc}")
    return apply_bootstrap_seed_to_workspace, create_workspace_from_starter


def _load_repository_context(root: Path):
    prepare_guided_action_package, load_repository, load_schema = _import_guided_action_runtime()
    repository = load_repository([root])
    schema = load_schema(SCHEMA_PATH)
    return repository, schema, prepare_guided_action_package


def _load_versioned_context():
    return _load_repository_context(VERSIONED_EXAMPLE_DIR)


def _update_artifact_header(path: Path, **updates: object) -> None:
    write_artifact_header, parse_artifact = _import_fixture_tools()
    artifact = parse_artifact(path)
    header = deepcopy(artifact.header)
    header.update(updates)
    write_artifact_header(path, header)


def _approval_record(*, actor_id: str, role: str, capability: str, recorded_at: str) -> dict:
    return {
        "reviewer": {
            "actor_id": actor_id,
            "role": role,
            "capability": capability,
            "display_name": actor_id,
        },
        "decision": "approve",
        "recorded_at": recorded_at,
        "related_transition": "in_review->approved",
    }


@contextmanager
def _git_fixture(example_dir: Path):
    temp_dir, fixture_root = init_git_example_repo(example_dir)
    try:
        yield fixture_root
    finally:
        temp_dir.cleanup()


def test_prepare_guided_action_package_builds_revise_package_for_current_brief_baseline():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    package = prepare_guided_action_package(
        repository,
        schema,
        feature_key="user-tag-bulk-import",
        request={
            "action_type": "revise_artifact_draft",
            "content_payload": {
                "title": "Retry-Safe Bulk Import Brief",
                "summary": "Clarify the revised problem framing.",
                "body_markdown": "# Goal\n\nClarify retry-safe operator guidance.\n",
            },
            "governance_payload": {
                "actor_id": "user:li.pm",
                "role": "pm",
                "capability": "artifact_authoring",
                "decision_authority": "brief_owner",
                "changed_at": "2026-03-25T16:20:00+08:00",
            },
        },
    )

    assert package["package_version"] == "v1"
    assert package["slice_stage"] == "brief_in_progress"
    assert package["recommended_by"]["surface"] == "get_delivery_slice_navigation"
    assert package["action"] == {"action_type": "revise_artifact_draft"}
    assert package["target"] == {
        "artifact_id": "BRIEF-2026-002",
        "artifact_type": "brief",
        "path": "12_brief_v0_2.md",
        "version": "v0.2",
    }
    assert package["preconditions"] == {
        "expected_slice_stage": "brief_in_progress",
        "expected_artifact_status": "draft",
        "expected_current_focus_artifact_id": "BRIEF-2026-002",
    }
    assert package["confirmation_summary"]["why"] == "Brief gate is not yet handoff-ready."


def test_prepare_guided_action_package_uses_draft_seed_when_brief_is_missing():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    package = prepare_guided_action_package(
        repository,
        schema,
        feature_key="brand-new-import",
        request={
            "action_type": "create_artifact_draft",
            "draft_seed": {
                "relative_path": "20_brief_v0_1.md",
                "artifact_id": "BRIEF-2026-900",
                "version": "v0.1",
                "title": "Brand New Import Brief",
                "summary": "Describe the first draft of the new import feature.",
                "scope_seed": {
                    "product_area": "growth",
                    "in_scope": ["brand-new import workflow"],
                    "out_of_scope": ["scheduled recurring imports"],
                },
            },
            "content_payload": {
                "body_markdown": "# Problem\n\nDescribe the initial brief.\n",
            },
            "governance_payload": {
                "actor_id": "user:li.pm",
                "role": "pm",
                "capability": "artifact_authoring",
                "decision_authority": "brief_owner",
                "changed_at": "2026-03-25T16:25:00+08:00",
            },
        },
    )

    assert package["slice_stage"] == "brief_missing"
    assert package["action"] == {"action_type": "create_artifact_draft"}
    assert package["target"] == {
        "artifact_id": "BRIEF-2026-900",
        "artifact_type": "brief",
        "path": "20_brief_v0_1.md",
        "version": "v0.1",
    }
    assert package["draft_seed"]["scope_seed"] == {
        "product_area": "growth",
        "in_scope": ["brand-new import workflow"],
        "out_of_scope": ["scheduled recurring imports"],
    }
    assert package["preconditions"] == {
        "expected_slice_stage": "brief_missing",
        "expected_current_focus_artifact_id": None,
    }


def test_prepare_guided_action_package_omits_content_payload_for_review_action():
    with _git_fixture(VERSIONED_EXAMPLE_DIR) as fixture_root:
        _update_artifact_header(
            fixture_root / "12_brief_v0_2.md",
            status="in_review",
            updated_at="2026-03-25T16:30:00+08:00",
            status_history=[],
        )
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)

        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "record_review_decision",
                "decision": "approve",
                "related_transition": "in_review->approved",
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "pm",
                    "decision_authority": "brief_owner",
                    "recorded_at": "2026-03-25T16:35:00+08:00",
                },
            },
        )

    assert package["action"] == {
        "action_type": "record_review_decision",
        "decision": "approve",
        "related_transition": "in_review->approved",
    }
    assert package["target"]["artifact_id"] == "BRIEF-2026-002"
    assert "content_payload" not in package


def test_prepare_guided_action_package_builds_promote_package_with_transition_preconditions():
    with _git_fixture(EXAMPLE_DIR) as fixture_root:
        (fixture_root / "02_prd.md").unlink()
        _update_artifact_header(
            fixture_root / "01_brief.md",
            status="in_review",
            updated_at="2026-03-25T16:40:00+08:00",
            status_history=[],
            downstream_refs=[],
        )
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)

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
                    "changed_at": "2026-03-25T16:45:00+08:00",
                },
            },
        )

    assert package["slice_stage"] == "brief_handoff_ready"
    assert package["action"] == {
        "action_type": "promote_artifact_status",
        "target_status": "approved",
    }
    assert package["target"]["artifact_id"] == "BRIEF-2026-001"
    assert package["preconditions"] == {
        "expected_slice_stage": "brief_handoff_ready",
        "expected_artifact_status": "in_review",
        "expected_current_focus_artifact_id": "BRIEF-2026-001",
        "expected_transition": {
            "from_status": "in_review",
            "to_status": "approved",
        },
    }


def test_prepare_guided_action_package_builds_validation_package_for_current_brief_baseline():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    package = prepare_guided_action_package(
        repository,
        schema,
        feature_key="user-tag-bulk-import",
        request={
            "action_type": "record_validation_result",
            "validation_payload": {
                "validator_name": "qa.smoke",
                "result": "pass",
                "recorded_at": "2026-03-28T11:00:00+08:00",
                "note": "Workspace-guided smoke remained green.",
            },
            "governance_payload": {
                "actor_id": "user:qin.qa",
                "role": "qa",
                "capability": "qa",
                "decision_authority": "qa_owner",
                "changed_at": "2026-03-28T11:00:00+08:00",
            },
        },
    )

    assert package["action"] == {"action_type": "record_validation_result"}
    assert package["target"]["artifact_id"] == "BRIEF-2026-002"
    assert package["validation_payload"] == {
        "validator_name": "qa.smoke",
        "result": "pass",
        "recorded_at": "2026-03-28T11:00:00+08:00",
        "note": "Workspace-guided smoke remained green.",
    }


def test_prepare_guided_action_package_allows_design_creation_at_prd_handoff_ready_in_minimal_workspace():
    apply_bootstrap_seed_to_workspace, create_workspace_from_starter = _import_workspace_bootstrap_runtime()

    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = create_workspace_from_starter("billing-intake", root=temp_dir)
        apply_bootstrap_seed_to_workspace(
            workspace,
            {
                "progression_level": "brief_plus_prd_seed",
                "brief_draft": {
                    "artifact_id": "BRIEF-2026-910",
                    "title": "Billing Intake Brief",
                    "summary": "Clarify the billing intake slice.",
                    "body_markdown": "## Background\n\nClarify the billing intake slice.\n",
                    "scope": {
                        "product_area": "growth",
                        "feature_key": "billing-intake",
                        "in_scope": ["billing intake workflow"],
                    },
                },
                "prd_seed_draft": {
                    "artifact_id": "PRD-2026-910",
                    "title": "Billing Intake PRD",
                    "summary": "Shape the billing intake requirement slice.",
                    "body_markdown": "## User Scenarios\n\n- Clarify billing intake.\n",
                    "scope": {
                        "product_area": "growth",
                        "feature_key": "billing-intake",
                        "in_scope": ["billing intake workflow"],
                    },
                },
                "evidence_map": {
                    "evidence_backed_facts": ["Billing intake needs a governed baseline."],
                    "derived_inferences": ["A PRD seed is justified."],
                    "missing_evidence": [],
                },
                "scope_assumptions": [],
                "open_questions": [],
                "next_handoff_recommendation": {
                    "role": "pm",
                    "action": "continue_prd_shaping",
                    "reason": "The slice is ready for PM-led refinement before design kickoff.",
                    "progression_level": "brief_plus_prd_seed",
                },
            },
        )

        workspace_root = workspace.active_repository_path
        _update_artifact_header(
            workspace_root / "01_brief.md",
            review_records=[
                _approval_record(
                    actor_id="user:li.pm",
                    role="pm",
                    capability="pm",
                    recorded_at="2026-04-02T10:00:00+08:00",
                )
            ],
            open_questions=[],
            updated_at="2026-04-02T10:00:00+08:00",
        )
        _update_artifact_header(
            workspace_root / "02_prd.md",
            review_records=[
                _approval_record(
                    actor_id="user:zhou.tl",
                    role="tech_lead",
                    capability="tech_lead",
                    recorded_at="2026-04-02T10:05:00+08:00",
                ),
                _approval_record(
                    actor_id="user:qin.qa",
                    role="qa",
                    capability="qa",
                    recorded_at="2026-04-02T10:06:00+08:00",
                ),
            ],
            open_questions=[],
            updated_at="2026-04-02T10:06:00+08:00",
        )

        repository, schema, prepare_guided_action_package = _load_repository_context(workspace_root)
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="billing-intake",
            request={
                "action_type": "create_artifact_draft",
                "draft_seed": {
                    "relative_path": "03_solution_design.md",
                    "artifact_id": "DESIGN-2026-910",
                    "version": "v0.1",
                    "title": "Billing Intake Design",
                    "summary": "Create the first billing intake solution design.",
                    "scope_seed": {
                        "product_area": "growth",
                        "in_scope": ["billing intake workflow"],
                    },
                },
                "content_payload": {
                    "body_markdown": "# Solution Summary\n\nDraft the billing intake design.\n",
                },
                "governance_payload": {
                    "actor_id": "user:zhou.tl",
                    "role": "tech_lead",
                    "capability": "artifact_authoring",
                    "decision_authority": "design_owner",
                    "changed_at": "2026-04-02T10:10:00+08:00",
                },
            },
        )

    assert package["slice_stage"] == "prd_handoff_ready"
    assert package["target"]["artifact_type"] == "solution_design"
    assert package["target"]["path"] == "03_solution_design.md"


def test_prepare_guided_action_package_requires_draft_seed_for_create():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    with pytest.raises(ValueError, match="draft_seed"):
        prepare_guided_action_package(
            repository,
            schema,
            feature_key="brand-new-import",
            request={
                "action_type": "create_artifact_draft",
                "content_payload": {
                    "body_markdown": "# Problem\n\nDescribe the initial brief.\n",
                },
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_authoring",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T16:50:00+08:00",
                },
            },
        )


def test_prepare_guided_action_package_requires_scope_seed_for_create():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    with pytest.raises(ValueError, match="scope_seed"):
        prepare_guided_action_package(
            repository,
            schema,
            feature_key="brand-new-import",
            request={
                "action_type": "create_artifact_draft",
                "draft_seed": {
                    "relative_path": "20_brief_v0_1.md",
                    "artifact_id": "BRIEF-2026-900",
                    "version": "v0.1",
                    "title": "Brand New Import Brief",
                    "summary": "Describe the first draft of the new import feature.",
                },
                "content_payload": {
                    "body_markdown": "# Problem\n\nDescribe the initial brief.\n",
                },
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_authoring",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T16:52:00+08:00",
                },
            },
        )


def test_prepare_guided_action_package_requires_body_markdown_for_revise():
    repository, schema, prepare_guided_action_package = _load_versioned_context()

    with pytest.raises(ValueError, match="body_markdown"):
        prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "revise_artifact_draft",
                "content_payload": {
                    "title": "Retry-Safe Bulk Import Brief",
                    "summary": "Clarify the revised problem framing.",
                },
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_authoring",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T16:55:00+08:00",
                },
            },
        )


def test_prepare_guided_action_package_requires_target_status_for_promote():
    with _git_fixture(EXAMPLE_DIR) as fixture_root:
        (fixture_root / "02_prd.md").unlink()
        _update_artifact_header(
            fixture_root / "01_brief.md",
            status="in_review",
            updated_at="2026-03-25T16:40:00+08:00",
            status_history=[],
            downstream_refs=[],
        )
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)

        with pytest.raises(ValueError, match="target_status"):
            prepare_guided_action_package(
                repository,
                schema,
                feature_key="user-tag-bulk-import",
                request={
                    "action_type": "promote_artifact_status",
                    "governance_payload": {
                        "actor_id": "user:li.pm",
                        "role": "pm",
                        "capability": "artifact_governance",
                        "decision_authority": "brief_owner",
                        "changed_at": "2026-03-25T17:00:00+08:00",
                        },
                    },
                )


def test_execute_guided_action_package_revises_current_brief_draft():
    execute_guided_action_package = _import_guided_action_executor()
    _, parse_artifact = _import_fixture_tools()

    with _git_fixture(VERSIONED_EXAMPLE_DIR) as fixture_root:
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)
        source_artifact = parse_artifact(fixture_root / "12_brief_v0_2.md")
        updated_body = source_artifact.body.replace(
            "transient commit failures create confusion unless the handoff explicitly describes retry-safe operator behavior.",
            "transient commit failures create confusion unless the handoff explicitly describes retry-safe operator behavior and support escalation steps.",
        )
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "revise_artifact_draft",
                "content_payload": {
                    "title": source_artifact.title,
                    "summary": "Clarify retry-safe operator guidance and support escalation.",
                    "body_markdown": updated_body,
                },
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_authoring",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T17:05:00+08:00",
                },
            },
        )

        result = execute_guided_action_package(
            fixture_root,
            package=package,
            schema_path=SCHEMA_PATH,
        )

        artifact = parse_artifact(fixture_root / "12_brief_v0_2.md")

    assert result["accepted"] is True
    assert result["executed_action"] == "revise_artifact_draft"
    assert result["artifact_id"] == "BRIEF-2026-002"
    assert "support escalation steps" in artifact.body
    assert artifact.header["summary"] == "Clarify retry-safe operator guidance and support escalation."


def test_execute_guided_action_package_records_review_decision():
    execute_guided_action_package = _import_guided_action_executor()
    _, parse_artifact = _import_fixture_tools()

    with _git_fixture(VERSIONED_EXAMPLE_DIR) as fixture_root:
        _update_artifact_header(
            fixture_root / "12_brief_v0_2.md",
            status="in_review",
            updated_at="2026-03-25T17:10:00+08:00",
            status_history=[],
        )
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "record_review_decision",
                "decision": "approve",
                "related_transition": "in_review->approved",
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "pm",
                    "decision_authority": "brief_owner",
                    "recorded_at": "2026-03-25T17:15:00+08:00",
                },
            },
        )

        result = execute_guided_action_package(
            fixture_root,
            package=package,
            schema_path=SCHEMA_PATH,
        )

        artifact = parse_artifact(fixture_root / "12_brief_v0_2.md")

    assert result["accepted"] is True
    assert result["executed_action"] == "record_review_decision"
    assert result["artifact_id"] == "BRIEF-2026-002"
    assert artifact.header["review_records"][-1]["decision"] == "approve"
    assert artifact.header["review_records"][-1]["reviewer"]["actor_id"] == "user:li.pm"


def test_execute_guided_action_package_records_validation_result():
    execute_guided_action_package = _import_guided_action_executor()
    _, parse_artifact = _import_fixture_tools()

    with _git_fixture(VERSIONED_EXAMPLE_DIR) as fixture_root:
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="user-tag-bulk-import",
            request={
                "action_type": "record_validation_result",
                "validation_payload": {
                    "validator_name": "qa.smoke",
                    "result": "pass",
                    "recorded_at": "2026-03-28T11:05:00+08:00",
                    "note": "Validation remained green after guided execution.",
                },
                "governance_payload": {
                    "actor_id": "user:qin.qa",
                    "role": "qa",
                    "capability": "qa",
                    "decision_authority": "qa_owner",
                    "changed_at": "2026-03-28T11:05:00+08:00",
                },
            },
        )

        result = execute_guided_action_package(
            fixture_root,
            package=package,
            schema_path=SCHEMA_PATH,
        )

        artifact = parse_artifact(fixture_root / "12_brief_v0_2.md")

    assert result["accepted"] is True
    assert result["executed_action"] == "record_validation_result"
    assert result["artifact_id"] == "BRIEF-2026-002"
    assert artifact.header["validation_records"][-1]["validator_name"] == "qa.smoke"


def test_execute_guided_action_package_rejects_stale_navigation_context():
    execute_guided_action_package = _import_guided_action_executor()

    with _git_fixture(EXAMPLE_DIR) as fixture_root:
        (fixture_root / "02_prd.md").unlink()
        _update_artifact_header(
            fixture_root / "01_brief.md",
            status="in_review",
            updated_at="2026-03-25T17:20:00+08:00",
            status_history=[],
            downstream_refs=[],
        )
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)
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
                    "changed_at": "2026-03-25T17:25:00+08:00",
                },
            },
        )

        _update_artifact_header(
            fixture_root / "01_brief.md",
            status="draft",
            updated_at="2026-03-25T17:26:00+08:00",
            review_records=[],
            status_history=[],
            downstream_refs=[],
        )

        result = execute_guided_action_package(
            fixture_root,
            package=package,
            schema_path=SCHEMA_PATH,
        )

    assert result["accepted"] is False
    assert result["rejection_code"] == "stale_navigation_context"
    assert result["current_state"] == {
        "slice_stage": "brief_in_progress",
        "current_focus_artifact_id": "BRIEF-2026-001",
    }


def test_execute_guided_action_package_creates_requested_brief_draft():
    execute_guided_action_package = _import_guided_action_executor()
    _, parse_artifact = _import_fixture_tools()

    with _git_fixture(EXAMPLE_DIR) as fixture_root:
        repository, schema, prepare_guided_action_package = _load_repository_context(fixture_root)
        source_artifact = parse_artifact(fixture_root / "01_brief.md")
        package = prepare_guided_action_package(
            repository,
            schema,
            feature_key="brand-new-import",
            request={
                "action_type": "create_artifact_draft",
                "draft_seed": {
                    "relative_path": "20_brief_v0_1.md",
                    "artifact_id": "BRIEF-2026-900",
                    "version": "v0.1",
                    "title": "Brand New Import Brief",
                    "summary": "Describe the initial draft of the new import feature.",
                    "scope_seed": {
                        "product_area": "growth",
                        "in_scope": ["brand-new import workflow"],
                    },
                },
                "content_payload": {
                    "body_markdown": source_artifact.body.replace(
                        "Operations staff currently add user tags one account at a time.",
                        "Operations staff need a first draft for a brand-new import workflow.",
                    ).replace(
                        "GOAL-001",
                        "GOAL-900",
                    ),
                },
                "governance_payload": {
                    "actor_id": "user:li.pm",
                    "role": "pm",
                    "capability": "artifact_authoring",
                    "decision_authority": "brief_owner",
                    "changed_at": "2026-03-25T17:30:00+08:00",
                },
            },
        )

        result = execute_guided_action_package(
            fixture_root,
            package=package,
            schema_path=SCHEMA_PATH,
        )

        artifact = parse_artifact(fixture_root / "20_brief_v0_1.md")

    assert result["accepted"] is True
    assert result["executed_action"] == "create_artifact_draft"
    assert result["artifact_id"] == "BRIEF-2026-900"
    assert artifact.header["artifact_id"] == "BRIEF-2026-900"
    assert artifact.header["summary"] == "Describe the initial draft of the new import feature."
    assert "brand-new import workflow" in artifact.body
