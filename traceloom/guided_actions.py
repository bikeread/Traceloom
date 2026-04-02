from __future__ import annotations

from os.path import commonpath
from pathlib import Path

from traceloom.defaults import resolve_default_schema_path
from traceloom.navigation import get_delivery_slice_navigation
from traceloom.repository import Repository, load_repository
from traceloom.validators import load_schema
from traceloom.write_ops import (
    create_artifact_draft,
    promote_artifact_status,
    record_review_decision,
    record_validation_result,
    revise_artifact_draft,
)


ALLOWED_ACTION_TYPES = {
    "create_artifact_draft",
    "revise_artifact_draft",
    "record_review_decision",
    "record_validation_result",
    "promote_artifact_status",
}
CREATE_TARGET_BY_STAGE = {
    "brief_missing": "brief",
    "prd_missing": "prd_story_pack",
    "design_missing": "solution_design",
    "brief_handoff_ready": "prd_story_pack",
    "prd_handoff_ready": "solution_design",
}
IN_PROGRESS_STAGES = {
    "brief_in_progress",
    "prd_in_progress",
    "design_in_progress",
}
HANDOFF_READY_STAGES = {
    "brief_handoff_ready",
    "prd_handoff_ready",
    "design_handoff_ready",
}
ARTIFACT_LABELS = {
    "brief": "Brief",
    "prd_story_pack": "PRD",
    "solution_design": "Design",
}
DEFAULT_SCHEMA_PATH = resolve_default_schema_path(module_file=__file__)


def prepare_guided_action_package(
    repository: Repository,
    schema: dict,
    *,
    feature_key: str,
    request: dict,
) -> dict:
    navigation = get_delivery_slice_navigation(repository, schema, feature_key)
    current_artifact = _resolve_current_focus_artifact(repository, navigation)
    normalized_request = _validate_guided_action_request(
        navigation,
        request,
        current_artifact=current_artifact,
    )
    return _build_guided_action_package(
        repository,
        feature_key=feature_key,
        navigation=navigation,
        current_artifact=current_artifact,
        request=normalized_request,
    )


def execute_guided_action_package(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    repository = load_repository([Path(repo_root)])
    schema = load_schema(schema_path)
    rejection = _check_execution_preconditions(repository, schema, package)
    if rejection is not None:
        return rejection

    result = _dispatch_guided_action(
        repo_root,
        package=package,
        schema_path=schema_path,
    )
    return {
        "accepted": True,
        "executed_action": package["action"]["action_type"],
        "artifact_id": package["target"]["artifact_id"],
        "result": result,
    }


def _validate_guided_action_request(
    navigation: dict,
    request: object,
    *,
    current_artifact,
) -> dict:
    if not isinstance(request, dict):
        raise ValueError("request must be a dict")

    action_type = request.get("action_type")
    if action_type not in ALLOWED_ACTION_TYPES:
        raise ValueError(f"unsupported action_type '{action_type}'")

    normalized = {
        "action_type": action_type,
        "governance_payload": _validate_governance_payload(
            action_type,
            request.get("governance_payload"),
        ),
    }

    if action_type in {"create_artifact_draft", "revise_artifact_draft"}:
        normalized["content_payload"] = _validate_content_payload(request.get("content_payload"))

    slice_stage = navigation["slice_stage"]

    if action_type == "create_artifact_draft":
        if slice_stage not in CREATE_TARGET_BY_STAGE:
            raise ValueError("create_artifact_draft only supports missing first-slice stages")
        normalized["draft_seed"] = _validate_draft_seed(request.get("draft_seed"))
        return normalized

    if current_artifact is None:
        raise ValueError(f"{action_type} requires a current focus artifact")

    if action_type == "revise_artifact_draft":
        if slice_stage not in IN_PROGRESS_STAGES:
            raise ValueError("revise_artifact_draft only supports in-progress first-slice stages")
        return normalized

    if action_type == "record_review_decision":
        decision = request.get("decision")
        if not isinstance(decision, str) or not decision:
            raise ValueError("decision is required")
        normalized["decision"] = decision

        related_transition = request.get("related_transition")
        if related_transition is not None:
            if not isinstance(related_transition, str) or not related_transition:
                raise ValueError("related_transition must be a non-empty string")
            normalized["related_transition"] = related_transition
        return normalized

    if action_type == "record_validation_result":
        normalized["validation_payload"] = _validate_validation_payload(request.get("validation_payload"))
        return normalized

    if slice_stage not in HANDOFF_READY_STAGES:
        raise ValueError("promote_artifact_status only supports handoff-ready first-slice stages")

    target_status = request.get("target_status")
    if not isinstance(target_status, str) or not target_status:
        raise ValueError("target_status is required")
    normalized["target_status"] = target_status
    return normalized


def _validate_governance_payload(action_type: str, payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("governance_payload must be a dict")

    actor_id = payload.get("actor_id")
    role = payload.get("role")
    if not isinstance(actor_id, str) or not actor_id:
        raise ValueError("governance_payload.actor_id is required")
    if not isinstance(role, str) or not role:
        raise ValueError("governance_payload.role is required")

    timestamp_field = "recorded_at" if action_type == "record_review_decision" else "changed_at"
    timestamp_value = payload.get(timestamp_field)
    if not isinstance(timestamp_value, str) or not timestamp_value:
        raise ValueError(f"governance_payload.{timestamp_field} is required")

    return dict(payload)


def _validate_content_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("content_payload must be a dict")

    body_markdown = payload.get("body_markdown")
    if not isinstance(body_markdown, str) or not body_markdown:
        raise ValueError("content_payload.body_markdown is required")

    return dict(payload)


def _validate_draft_seed(seed: object) -> dict:
    if not isinstance(seed, dict):
        raise ValueError("draft_seed is required")

    for field_name in ("relative_path", "artifact_id", "version", "title", "summary"):
        value = seed.get(field_name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"draft_seed.{field_name} is required")

    seed = dict(seed)
    seed["scope_seed"] = _validate_scope_seed(seed.get("scope_seed"))
    return seed


def _validate_validation_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("validation_payload must be a dict")

    validator_name = payload.get("validator_name")
    result = payload.get("result")
    recorded_at = payload.get("recorded_at")
    if not isinstance(validator_name, str) or not validator_name:
        raise ValueError("validation_payload.validator_name is required")
    if not isinstance(result, str) or not result:
        raise ValueError("validation_payload.result is required")
    if not isinstance(recorded_at, str) or not recorded_at:
        raise ValueError("validation_payload.recorded_at is required")

    normalized = {
        "validator_name": validator_name,
        "result": result,
        "recorded_at": recorded_at,
    }
    note = payload.get("note")
    if note is not None:
        if not isinstance(note, str) or not note:
            raise ValueError("validation_payload.note must be a non-empty string")
        normalized["note"] = note
    return normalized


def _validate_scope_seed(scope_seed: object) -> dict:
    if not isinstance(scope_seed, dict):
        raise ValueError("draft_seed.scope_seed is required")

    product_area = scope_seed.get("product_area")
    in_scope = scope_seed.get("in_scope")
    if not isinstance(product_area, str) or not product_area:
        raise ValueError("draft_seed.scope_seed.product_area is required")
    if not isinstance(in_scope, list) or not in_scope or not all(isinstance(item, str) and item for item in in_scope):
        raise ValueError("draft_seed.scope_seed.in_scope is required")

    normalized = {
        "product_area": product_area,
        "in_scope": list(in_scope),
    }
    out_of_scope = scope_seed.get("out_of_scope")
    if out_of_scope is not None:
        if not isinstance(out_of_scope, list) or not all(isinstance(item, str) for item in out_of_scope):
            raise ValueError("draft_seed.scope_seed.out_of_scope must be a list of strings")
        normalized["out_of_scope"] = list(out_of_scope)

    return normalized


def _build_guided_action_package(
    repository: Repository,
    *,
    feature_key: str,
    navigation: dict,
    current_artifact,
    request: dict,
) -> dict:
    action_type = request["action_type"]
    target = _build_target_payload(repository, navigation, current_artifact, request)

    package = {
        "package_version": "v1",
        "feature_key": feature_key,
        "slice_stage": navigation["slice_stage"],
        "recommended_by": {
            "surface": "get_delivery_slice_navigation",
            "generated_at": _extract_generated_at(request["governance_payload"]),
        },
        "action": _build_action_payload(request),
        "target": target,
        "governance_payload": request["governance_payload"],
        "preconditions": _build_preconditions(navigation, current_artifact, request),
        "confirmation_summary": {
            "title": _build_confirmation_title(action_type, target["artifact_type"]),
            "why": _build_confirmation_why(navigation, action_type, target["artifact_type"]),
        },
    }
    if action_type in {"create_artifact_draft", "revise_artifact_draft"}:
        package["content_payload"] = request["content_payload"]
    if action_type == "create_artifact_draft":
        package["draft_seed"] = request["draft_seed"]
    if action_type == "record_validation_result":
        package["validation_payload"] = request["validation_payload"]
    return package


def _build_target_payload(
    repository: Repository,
    navigation: dict,
    current_artifact,
    request: dict,
) -> dict:
    if request["action_type"] == "create_artifact_draft":
        draft_seed = request["draft_seed"]
        return {
            "artifact_id": draft_seed["artifact_id"],
            "artifact_type": CREATE_TARGET_BY_STAGE[navigation["slice_stage"]],
            "path": draft_seed["relative_path"],
            "version": draft_seed["version"],
        }

    return {
        "artifact_id": current_artifact.artifact_id,
        "artifact_type": current_artifact.artifact_type,
        "path": _relative_artifact_path(repository, current_artifact.path),
        "version": current_artifact.header.get("version"),
    }


def _build_action_payload(request: dict) -> dict:
    action = {"action_type": request["action_type"]}
    if "decision" in request:
        action["decision"] = request["decision"]
    if "related_transition" in request:
        action["related_transition"] = request["related_transition"]
    if "target_status" in request:
        action["target_status"] = request["target_status"]
    return action


def _build_preconditions(navigation: dict, current_artifact, request: dict) -> dict:
    preconditions = {
        "expected_slice_stage": navigation["slice_stage"],
        "expected_current_focus_artifact_id": navigation["current_focus"]["artifact_id"],
    }
    if current_artifact is not None:
        preconditions["expected_artifact_status"] = current_artifact.status
    if request["action_type"] == "promote_artifact_status" and current_artifact is not None:
        preconditions["expected_transition"] = {
            "from_status": current_artifact.status,
            "to_status": request["target_status"],
        }
    return preconditions


def _build_confirmation_title(action_type: str, artifact_type: str) -> str:
    label = ARTIFACT_LABELS.get(artifact_type, artifact_type.replace("_", " ").title())
    if action_type == "create_artifact_draft":
        return f"Create {label} draft"
    if action_type == "revise_artifact_draft":
        return f"Revise {label} draft"
    if action_type == "record_review_decision":
        return f"Record {label} review decision"
    if action_type == "record_validation_result":
        return f"Record {label} validation result"
    return f"Promote {label} status"


def _build_confirmation_why(navigation: dict, action_type: str, artifact_type: str) -> str:
    for recommendation in navigation.get("next_recommended_actions", []):
        if recommendation.get("action_type") == action_type:
            why = recommendation.get("why")
            if isinstance(why, str) and why:
                return why

    label = ARTIFACT_LABELS.get(artifact_type, artifact_type.replace("_", " "))
    if action_type == "record_review_decision":
        return f"{label} review feedback is ready to be recorded."
    if action_type == "record_validation_result":
        return f"{label} validation evidence is ready to be recorded."
    if action_type == "promote_artifact_status":
        return f"{label} handoff is ready for a governed status promotion."
    if action_type == "create_artifact_draft":
        return f"{label} draft is missing and needs to be created."
    return f"{label} draft remains editable and can be revised."


def _extract_generated_at(governance_payload: dict) -> str:
    if "changed_at" in governance_payload:
        return governance_payload["changed_at"]
    return governance_payload["recorded_at"]


def _resolve_current_focus_artifact(repository: Repository, navigation: dict):
    artifact_id = navigation["current_focus"]["artifact_id"]
    if artifact_id is None:
        return None
    return repository.artifacts_by_id.get(artifact_id)


def _relative_artifact_path(repository: Repository, artifact_path: Path) -> str:
    repo_root = _infer_repository_root(repository)
    resolved_artifact_path = artifact_path.resolve()
    try:
        return str(resolved_artifact_path.relative_to(repo_root))
    except ValueError:
        return artifact_path.name


def _infer_repository_root(repository: Repository) -> Path:
    artifact_dirs = [str(artifact.path.resolve().parent) for artifact in repository.artifacts_by_id.values()]
    return Path(commonpath(artifact_dirs))


def _check_execution_preconditions(repository: Repository, schema: dict, package: dict) -> dict | None:
    navigation = get_delivery_slice_navigation(repository, schema, package["feature_key"])
    current_state = {
        "slice_stage": navigation["slice_stage"],
        "current_focus_artifact_id": navigation["current_focus"]["artifact_id"],
    }
    expected_slice_stage = package["preconditions"]["expected_slice_stage"]
    expected_focus_artifact_id = package["preconditions"]["expected_current_focus_artifact_id"]
    if navigation["slice_stage"] != expected_slice_stage or navigation["current_focus"]["artifact_id"] != expected_focus_artifact_id:
        return {
            "accepted": False,
            "rejection_code": "stale_navigation_context",
            "message": "The current slice stage no longer matches the confirmed action package.",
            "current_state": current_state,
        }

    action_type = package["action"]["action_type"]
    if action_type == "create_artifact_draft":
        return None

    target_artifact = repository.artifacts_by_id.get(package["target"]["artifact_id"])
    if target_artifact is None:
        return {
            "accepted": False,
            "rejection_code": "artifact_not_found",
            "message": "The target artifact no longer exists in the repository.",
            "current_state": current_state,
        }

    expected_status = package["preconditions"].get("expected_artifact_status")
    if expected_status is not None and target_artifact.status != expected_status:
        rejection_code = (
            "artifact_no_longer_editable"
            if action_type in {"revise_artifact_draft", "record_review_decision", "record_validation_result"}
            else "stale_navigation_context"
        )
        return {
            "accepted": False,
            "rejection_code": rejection_code,
            "message": "The target artifact no longer matches the confirmed action package.",
            "current_state": current_state,
        }

    return None


def _dispatch_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    action_type = package["action"]["action_type"]
    if action_type == "create_artifact_draft":
        return _dispatch_create_guided_action(repo_root, package=package, schema_path=schema_path)
    if action_type == "revise_artifact_draft":
        return _dispatch_revise_guided_action(repo_root, package=package, schema_path=schema_path)
    if action_type == "record_review_decision":
        return _dispatch_review_guided_action(repo_root, package=package, schema_path=schema_path)
    if action_type == "record_validation_result":
        return _dispatch_validation_guided_action(repo_root, package=package, schema_path=schema_path)
    return _dispatch_promote_guided_action(repo_root, package=package, schema_path=schema_path)


def _dispatch_create_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    draft_seed = package["draft_seed"]
    governance_payload = package["governance_payload"]
    create_result = create_artifact_draft(
        repo_root,
        relative_path=draft_seed["relative_path"],
        artifact_type=package["target"]["artifact_type"],
        artifact_id=draft_seed["artifact_id"],
        title=draft_seed["title"],
        summary=draft_seed["summary"],
        version=draft_seed["version"],
        owner=_build_actor_ref(governance_payload),
        scope=_build_scope_payload(draft_seed["scope_seed"], feature_key=package["feature_key"]),
        created_at=governance_payload["changed_at"],
        schema_path=schema_path,
    )

    content_payload = package.get("content_payload", {})
    body_markdown = content_payload.get("body_markdown")
    if not isinstance(body_markdown, str) or not body_markdown:
        return create_result

    header_updates = {
        field_name: content_payload[field_name]
        for field_name in ("title", "summary")
        if isinstance(content_payload.get(field_name), str) and content_payload.get(field_name)
    }
    return revise_artifact_draft(
        repo_root,
        artifact_id=draft_seed["artifact_id"],
        body=body_markdown,
        header_updates=header_updates or None,
        updated_at=governance_payload["changed_at"],
        schema_path=schema_path,
    )


def _dispatch_revise_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    content_payload = package["content_payload"]
    header_updates = {
        field_name: content_payload[field_name]
        for field_name in ("title", "summary")
        if isinstance(content_payload.get(field_name), str) and content_payload.get(field_name)
    }
    return revise_artifact_draft(
        repo_root,
        artifact_id=package["target"]["artifact_id"],
        body=content_payload["body_markdown"],
        header_updates=header_updates or None,
        updated_at=package["governance_payload"]["changed_at"],
        schema_path=schema_path,
    )


def _dispatch_review_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    action = package["action"]
    governance_payload = package["governance_payload"]
    review_record = {
        "reviewer": _build_actor_ref(governance_payload),
        "decision": action["decision"],
        "recorded_at": governance_payload["recorded_at"],
    }
    if "related_transition" in action:
        review_record["related_transition"] = action["related_transition"]

    return record_review_decision(
        repo_root,
        artifact_id=package["target"]["artifact_id"],
        review_record=review_record,
        schema_path=schema_path,
    )


def _dispatch_validation_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    return record_validation_result(
        repo_root,
        artifact_id=package["target"]["artifact_id"],
        validation_record=dict(package["validation_payload"]),
        schema_path=schema_path,
    )


def _dispatch_promote_guided_action(
    repo_root: str | Path,
    *,
    package: dict,
    schema_path: str | Path,
) -> dict:
    return promote_artifact_status(
        repo_root,
        artifact_id=package["target"]["artifact_id"],
        target_status=package["action"]["target_status"],
        changed_by=_build_actor_ref(package["governance_payload"]),
        changed_at=package["governance_payload"]["changed_at"],
        schema_path=schema_path,
    )


def _build_actor_ref(governance_payload: dict) -> dict:
    actor_ref = {
        "actor_id": governance_payload["actor_id"],
        "role": governance_payload["role"],
    }
    if isinstance(governance_payload.get("capability"), str) and governance_payload.get("capability"):
        actor_ref["capability"] = governance_payload["capability"]
    if isinstance(governance_payload.get("decision_authority"), str) and governance_payload.get("decision_authority"):
        actor_ref["decision_authority"] = governance_payload["decision_authority"]
    return actor_ref


def _build_scope_payload(scope_seed: dict, *, feature_key: str) -> dict:
    scope = {
        "product_area": scope_seed["product_area"],
        "feature_key": feature_key,
        "in_scope": list(scope_seed["in_scope"]),
    }
    if "out_of_scope" in scope_seed:
        scope["out_of_scope"] = list(scope_seed["out_of_scope"])
    return scope
