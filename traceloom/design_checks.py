from __future__ import annotations

from traceloom.navigation import get_delivery_slice_navigation
from traceloom.queries import get_artifact_feature_key
from traceloom.repository import Repository
from traceloom.workflows import evaluate_artifact_workflow


def check_design_completeness(repository: Repository, schema: dict, feature_key: str) -> dict:
    navigation = get_delivery_slice_navigation(repository, schema, feature_key)
    artifacts = _select_baseline_artifacts(repository, feature_key)
    brief = artifacts["brief"]
    prd = artifacts["prd_story_pack"]
    design = artifacts["solution_design"]

    blocking_items: list[dict] = []
    if brief is None:
        blocking_items.append({"kind": "missing_brief_artifact", "artifact_type": "brief"})
    if prd is None:
        blocking_items.append({"kind": "missing_prd_artifact", "artifact_type": "prd_story_pack"})
    if design is None and prd is not None:
        blocking_items.append({"kind": "missing_design_artifact", "artifact_type": "solution_design"})

    if navigation["slice_stage"] in {"brief_missing", "brief_in_progress", "brief_handoff_ready", "prd_in_progress"}:
        blocking_items.extend(_navigation_blockers(navigation))

    design_workflow = None
    if design is not None:
        blocking_items.extend(_collect_design_coverage_blockers(repository, prd, design))
        design_workflow = evaluate_artifact_workflow(repository, schema, design.artifact_id)
        if design_workflow["current_outcome"] not in {"approved", "waived"}:
            blocking_items.extend(_workflow_blockers(design_workflow))

    recommendations = _build_recommendations(navigation, design, blocking_items)
    artifact_ids = [
        artifact.artifact_id
        for artifact in (brief, prd, design)
        if artifact is not None
    ]

    return {
        "feature_key": feature_key,
        "slice_stage": navigation["slice_stage"],
        "artifact_ids": artifact_ids,
        "design_artifact_id": None if design is None else design.artifact_id,
        "ready": not blocking_items,
        "blocker_count": len(blocking_items),
        "blocking_items": blocking_items,
        "recommendations": recommendations,
    }


def _select_baseline_artifacts(repository: Repository, feature_key: str) -> dict[str, object | None]:
    return {
        artifact_type: _select_baseline_artifact(repository, feature_key, artifact_type)
        for artifact_type in ("brief", "prd_story_pack", "solution_design")
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

    return sorted(
        current_candidates,
        key=lambda artifact: (_version_sort_key(artifact.header.get("version")), artifact.artifact_id),
    )[-1]


def _version_sort_key(value: object) -> tuple:
    if not isinstance(value, str):
        return (value,)

    normalized: list[object] = []
    for chunk in value.replace("-", ".").split("."):
        if chunk.isdigit():
            normalized.append(int(chunk))
        else:
            normalized.append(chunk)
    return tuple(normalized)


def _navigation_blockers(navigation: dict) -> list[dict]:
    blockers: list[dict] = []
    for item in navigation.get("blocking_items", []):
        if isinstance(item, dict):
            blockers.append(dict(item))
    if not blockers:
        blockers.append(
            {
                "kind": "upstream_slice_not_ready",
                "slice_stage": navigation["slice_stage"],
            }
        )
    return blockers


def _collect_design_coverage_blockers(repository: Repository, prd, design) -> list[dict]:
    if prd is None or design is None:
        return []

    covered_req_ids: set[str] = set()
    covered_nfr_ids: set[str] = set()
    for edge in repository.relation_edges_by_id.values():
        if edge.get("relation_type") != "covers":
            continue
        from_endpoint = edge.get("from", {})
        to_endpoint = edge.get("to", {})
        if from_endpoint.get("kind") != "trace_unit" or to_endpoint.get("kind") != "trace_unit":
            continue
        if from_endpoint.get("artifact_id") != prd.artifact_id:
            continue
        if to_endpoint.get("artifact_id") != design.artifact_id or to_endpoint.get("type") != "DEC":
            continue
        if from_endpoint.get("type") == "REQ":
            covered_req_ids.add(from_endpoint["id"])
        elif from_endpoint.get("type") == "NFR":
            covered_nfr_ids.add(from_endpoint["id"])

    blockers: list[dict] = []
    for unit in prd.trace_units:
        if not isinstance(unit, dict):
            continue
        unit_id = unit.get("id")
        if not isinstance(unit_id, str):
            continue
        if unit.get("type") == "REQ" and unit_id not in covered_req_ids:
            blockers.append(
                {
                    "kind": "missing_requirement_coverage",
                    "upstream_unit_id": unit_id,
                    "required_relation_type": "covers",
                    "target_artifact_id": design.artifact_id,
                }
            )
        elif unit.get("type") == "NFR" and unit_id not in covered_nfr_ids:
            blockers.append(
                {
                    "kind": "missing_nfr_coverage",
                    "upstream_unit_id": unit_id,
                    "required_relation_type": "covers",
                    "target_artifact_id": design.artifact_id,
                }
            )
    return blockers


def _workflow_blockers(payload: dict) -> list[dict]:
    blockers: list[dict] = []
    for item in payload.get("blocking_reasons", []):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        if kind == "missing_approval_capability":
            blockers.append(
                {
                    "kind": "missing_design_approval_capability",
                    "capability": item.get("capability"),
                }
            )
        elif kind == "open_question":
            blockers.append(
                {
                    "kind": "design_open_question",
                    "q_id": item.get("q_id"),
                    "status": item.get("status"),
                    "note": item.get("note"),
                }
            )
        elif kind == "validation_issue":
            blockers.append(
                {
                    "kind": "design_validation_issue",
                    "code": item.get("code"),
                    "object_id": item.get("object_id"),
                    "message": item.get("message"),
                }
            )
        elif kind == "review_decision":
            blockers.append(
                {
                    "kind": "design_review_decision",
                    "decision": item.get("decision"),
                }
            )
        elif kind == "unsatisfied_dependency":
            blockers.append(
                {
                    "kind": "design_dependency_blocked",
                    "gate_id": item.get("gate_id"),
                    "outcome": item.get("outcome"),
                }
            )
        else:
            blockers.append(dict(item))
    return blockers


def _build_recommendations(navigation: dict, design, blocking_items: list[dict]) -> list[dict]:
    if not blocking_items:
        return []

    if any(item.get("kind") == "missing_design_artifact" for item in blocking_items):
        return [
            {
                "action_type": "create_artifact_draft",
                "target_artifact_id": None,
                "why": "PRD is present, but the solution design artifact has not been created yet.",
            }
        ]

    if navigation["slice_stage"] in {"brief_missing", "brief_in_progress", "brief_handoff_ready", "prd_in_progress"}:
        return list(navigation.get("next_recommended_actions", []))

    if any(
        item.get("kind")
        in {
            "missing_requirement_coverage",
            "missing_nfr_coverage",
            "design_validation_issue",
            "design_open_question",
            "design_review_decision",
        }
        for item in blocking_items
    ):
        return [
            {
                "action_type": "revise_artifact_draft",
                "target_artifact_id": None if design is None else design.artifact_id,
                "why": "Design coverage or design-stage blockers remain unresolved.",
            }
        ]

    if any(item.get("kind") == "missing_design_approval_capability" for item in blocking_items) and design is not None:
        return [
            {
                "action_type": "record_review_decision",
                "target_artifact_id": design.artifact_id,
                "why": "Design evidence is present, but required review approval is still missing.",
            }
        ]

    return list(navigation.get("next_recommended_actions", []))
