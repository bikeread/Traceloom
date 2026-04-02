from __future__ import annotations

from traceloom.queries import get_artifact_feature_key
from traceloom.repository import Repository
from traceloom.workflows import DEFAULT_GATE_POLICIES, evaluate_artifact_workflow


FIRST_SLICE_ORDER = ("brief", "prd_story_pack", "solution_design")
ARTIFACT_TYPE_TO_STAGE = {
    "brief": "brief",
    "prd_story_pack": "prd",
    "solution_design": "design",
}
NEXT_STAGE_BY_STAGE = {
    "brief": "prd",
    "prd": "design",
    "design": "execution",
}
NEXT_CAPABILITY_BY_STAGE = {
    "brief": "pm",
    "prd": "pm",
    "design": "tech_lead",
}
NEXT_ARTIFACT_BY_STAGE = {
    "brief": "brief",
    "prd": "prd_story_pack",
    "design": "solution_design",
}
GATE_ID_BY_ARTIFACT_TYPE = {
    policy.artifact_type: policy.gate_id for policy in DEFAULT_GATE_POLICIES
}


def get_delivery_slice_navigation(repository: Repository, schema: dict, feature_key: str) -> dict:
    artifacts = _select_slice_baselines(repository, feature_key)
    resolution = _resolve_slice_state(repository, schema, artifacts)
    return _build_navigation_payload(feature_key, artifacts, resolution)


def _select_slice_baselines(repository: Repository, feature_key: str) -> dict[str, object | None]:
    return {
        artifact_type: _select_baseline_artifact(repository, feature_key, artifact_type)
        for artifact_type in FIRST_SLICE_ORDER
    }


def _select_baseline_artifact(repository: Repository, feature_key: str, artifact_type: str):
    candidates = [
        artifact
        for artifact in repository.artifacts_by_id.values()
        if artifact.artifact_type == artifact_type and get_artifact_feature_key(artifact) == feature_key
    ]
    if not candidates:
        return None

    candidate_ids = {artifact.artifact_id for artifact in candidates}
    superseded_ids = {
        edge.get("to", {}).get("id")
        for edge in repository.relation_edges_by_id.values()
        if edge.get("relation_type") == "supersedes"
        and edge.get("from", {}).get("id") in candidate_ids
        and edge.get("to", {}).get("id") in candidate_ids
    }
    current_candidates = [artifact for artifact in candidates if artifact.artifact_id not in superseded_ids]
    if not current_candidates:
        current_candidates = candidates

    return sorted(current_candidates, key=_artifact_sort_key)[-1]


def _resolve_slice_state(repository: Repository, schema: dict, artifacts: dict[str, object | None]) -> dict:
    for artifact_type in FIRST_SLICE_ORDER:
        stage = ARTIFACT_TYPE_TO_STAGE[artifact_type]
        artifact = artifacts[artifact_type]
        if artifact is None:
            return {
                "slice_stage": f"{stage}_missing",
                "stage": stage,
                "artifact": None,
                "workflow": None,
            }

        workflow = evaluate_artifact_workflow(repository, schema, artifact.artifact_id)
        if workflow["current_outcome"] not in {"approved", "waived"}:
            return {
                "slice_stage": f"{stage}_in_progress",
                "stage": stage,
                "artifact": artifact,
                "workflow": workflow,
            }

        if artifact_type == "solution_design":
            return {
                "slice_stage": "design_handoff_ready",
                "stage": "design",
                "artifact": artifact,
                "workflow": workflow,
            }

        next_artifact_type = FIRST_SLICE_ORDER[FIRST_SLICE_ORDER.index(artifact_type) + 1]
        if artifacts[next_artifact_type] is None:
            return {
                "slice_stage": f"{stage}_handoff_ready",
                "stage": stage,
                "artifact": artifact,
                "workflow": workflow,
            }

    design_artifact = artifacts["solution_design"]
    design_workflow = evaluate_artifact_workflow(repository, schema, design_artifact.artifact_id)
    return {
        "slice_stage": "design_handoff_ready",
        "stage": "design",
        "artifact": design_artifact,
        "workflow": design_workflow,
    }


def _build_navigation_payload(feature_key: str, artifacts: dict[str, object | None], resolution: dict) -> dict:
    stage = resolution["stage"]
    artifact = resolution["artifact"]
    workflow = resolution["workflow"]
    next_stage = NEXT_STAGE_BY_STAGE[stage]
    slice_stage = resolution["slice_stage"]

    if workflow is None:
        blocking_items = []
        missing_conditions = [f"{stage}_artifact_created"]
        current_focus = {
            "artifact_id": None,
            "artifact_type": NEXT_ARTIFACT_BY_STAGE[stage],
            "gate_id": GATE_ID_BY_ARTIFACT_TYPE[NEXT_ARTIFACT_BY_STAGE[stage]],
            "outcome": "missing",
        }
    else:
        blocking_items = list(workflow["blocking_reasons"])
        missing_conditions = [] if workflow["current_outcome"] in {"approved", "waived"} else [f"{stage}_gate_approved_or_waived"]
        current_focus = {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "gate_id": workflow["gate_id"],
            "outcome": workflow["current_outcome"],
        }

    next_capability, next_artifact_type, actions = _build_recommendation(
        slice_stage=slice_stage,
        stage=stage,
        artifact=artifact,
        workflow=workflow,
    )

    return {
        "feature_key": feature_key,
        "slice_stage": slice_stage,
        "artifacts": {
            artifact_type: _serialize_artifact(artifacts[artifact_type])
            for artifact_type in FIRST_SLICE_ORDER
        },
        "current_focus": current_focus,
        "next_recommended_capability": next_capability,
        "next_recommended_artifact_type": next_artifact_type,
        "next_recommended_actions": actions,
        "blocking_items": blocking_items,
        "attention_items": [],
        "handoff_readiness": {
            "ready": slice_stage.endswith("_handoff_ready"),
            "target_stage": next_stage,
            "missing_conditions": missing_conditions,
        },
        "upcoming_handoff": {
            "from_stage": stage,
            "to_stage": next_stage,
        },
    }


def _build_recommendation(*, slice_stage: str, stage: str, artifact, workflow: dict | None) -> tuple[str, str, list[dict]]:
    if slice_stage.endswith("_missing"):
        return (
            NEXT_CAPABILITY_BY_STAGE[stage],
            NEXT_ARTIFACT_BY_STAGE[stage],
            [
                {
                    "action_type": "create_artifact_draft",
                    "target_artifact_id": None,
                    "why": f"{stage} artifact does not exist yet.",
                }
            ],
        )

    if slice_stage.endswith("_in_progress"):
        return (
            NEXT_CAPABILITY_BY_STAGE[stage],
            artifact.artifact_type,
            [
                {
                    "action_type": "revise_artifact_draft",
                    "target_artifact_id": artifact.artifact_id,
                    "why": f"{stage.capitalize()} gate is not yet handoff-ready.",
                }
            ],
        )

    if slice_stage == "prd_handoff_ready":
        return (
            "tech_lead",
            "solution_design",
            [
                {
                    "action_type": "create_artifact_draft",
                    "target_artifact_id": None,
                    "why": "PRD handoff is ready for design kickoff.",
                }
            ],
        )

    if slice_stage == "brief_handoff_ready":
        return (
            "pm",
            "prd_story_pack",
            [
                {
                    "action_type": "create_artifact_draft",
                    "target_artifact_id": None,
                    "why": "Brief handoff is ready for PRD drafting.",
                }
            ],
        )

    return (
        "tech_lead",
        "solution_design",
        [],
    )


def _serialize_artifact(artifact) -> dict | None:
    if artifact is None:
        return None
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "version": artifact.header.get("version"),
        "status": artifact.status,
        "path": str(artifact.path),
    }


def _artifact_sort_key(artifact) -> tuple:
    return (
        _version_sort_key(artifact.header.get("version")),
        artifact.artifact_id,
    )


def _version_sort_key(value: object) -> tuple:
    if not isinstance(value, str):
        return (value,)

    normalized: list[object] = []
    token = ""
    token_is_digit = False
    for character in value:
        if character.isdigit():
            if token and not token_is_digit:
                normalized.append(token.lower())
                token = ""
            token += character
            token_is_digit = True
        elif character.isalpha():
            if token and token_is_digit:
                normalized.append(int(token))
                token = ""
            token += character
            token_is_digit = False
        else:
            if token:
                normalized.append(int(token) if token_is_digit else token.lower())
                token = ""
    if token:
        normalized.append(int(token) if token_is_digit else token.lower())
    return tuple(normalized) or (value,)
