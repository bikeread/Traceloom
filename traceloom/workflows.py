from __future__ import annotations

from dataclasses import asdict, dataclass

from traceloom.queries import get_artifact_feature_key
from traceloom.repository import Repository
from traceloom.validators import serialize_issue, validate_repository


@dataclass(frozen=True, slots=True)
class GatePolicy:
    gate_id: str
    delivery_stage: str
    artifact_type: str
    enforcement: str
    required_approval_capabilities: tuple[str, ...]
    required_evidence: tuple[str, ...]
    depends_on_gates: tuple[str, ...]
    controls_transition: tuple[str, str]


DEFAULT_GATE_POLICIES = (
    GatePolicy(
        gate_id="brief_gate",
        delivery_stage="brief",
        artifact_type="brief",
        enforcement="blocking",
        required_approval_capabilities=("pm",),
        required_evidence=(),
        depends_on_gates=(),
        controls_transition=("in_review", "approved"),
    ),
    GatePolicy(
        gate_id="prd_gate",
        delivery_stage="prd",
        artifact_type="prd_story_pack",
        enforcement="blocking",
        required_approval_capabilities=("tech_lead", "qa"),
        required_evidence=(),
        depends_on_gates=("brief_gate",),
        controls_transition=("in_review", "approved"),
    ),
    GatePolicy(
        gate_id="design_gate",
        delivery_stage="design",
        artifact_type="solution_design",
        enforcement="blocking",
        required_approval_capabilities=("tech_lead",),
        required_evidence=(),
        depends_on_gates=("prd_gate",),
        controls_transition=("in_review", "approved"),
    ),
    GatePolicy(
        gate_id="execution_readiness_gate",
        delivery_stage="execution_readiness",
        artifact_type="execution_plan",
        enforcement="blocking",
        required_approval_capabilities=("tech_lead",),
        required_evidence=(),
        depends_on_gates=("design_gate",),
        controls_transition=("in_review", "approved"),
    ),
    GatePolicy(
        gate_id="test_case_gate",
        delivery_stage="test_case",
        artifact_type="test_acceptance",
        enforcement="blocking",
        required_approval_capabilities=("qa",),
        required_evidence=(),
        depends_on_gates=("execution_readiness_gate",),
        controls_transition=("in_review", "approved"),
    ),
    GatePolicy(
        gate_id="release_review_gate",
        delivery_stage="release_review",
        artifact_type="release_review",
        enforcement="blocking",
        required_approval_capabilities=("release_owner", "qa", "tech_lead"),
        required_evidence=(),
        depends_on_gates=("test_case_gate",),
        controls_transition=("in_review", "approved"),
    ),
)

_POLICY_BY_ARTIFACT_TYPE = {policy.artifact_type: policy for policy in DEFAULT_GATE_POLICIES}
_POLICY_BY_GATE_ID = {policy.gate_id: policy for policy in DEFAULT_GATE_POLICIES}


def list_default_gate_policies() -> list[dict]:
    policies: list[dict] = []
    for policy in DEFAULT_GATE_POLICIES:
        item = asdict(policy)
        item["required_approval_capabilities"] = list(policy.required_approval_capabilities)
        item["required_evidence"] = list(policy.required_evidence)
        item["depends_on_gates"] = list(policy.depends_on_gates)
        item["controls_transition"] = {
            "from_status": policy.controls_transition[0],
            "to_status": policy.controls_transition[1],
        }
        policies.append(item)
    return policies


def evaluate_artifact_workflow(repository: Repository, schema: dict, artifact_id: str) -> dict:
    return _evaluate_artifact_workflow(repository, schema, artifact_id, seen_artifact_ids=set())


def _evaluate_artifact_workflow(
    repository: Repository,
    schema: dict,
    artifact_id: str,
    *,
    seen_artifact_ids: set[str],
) -> dict:
    artifact = repository.artifacts_by_id[artifact_id]
    policy = _POLICY_BY_ARTIFACT_TYPE[artifact.artifact_type]
    next_seen = set(seen_artifact_ids)
    next_seen.add(artifact_id)
    approvals, decision_sources, decisions = _collect_review_evidence(artifact.header.get("review_records", []))
    required = list(policy.required_approval_capabilities)
    satisfied = sorted(capability for capability in required if capability in approvals)
    missing = [capability for capability in required if capability not in approvals]
    depends_on = _evaluate_dependencies(
        repository,
        schema,
        artifact,
        policy,
        seen_artifact_ids=next_seen,
    )
    open_question_reasons = _collect_open_question_reasons(artifact)
    validation_issue_reasons = _collect_validation_issue_reasons(repository, schema, artifact)

    if _has_unsatisfied_dependency(depends_on):
        blocking_reasons = [
            {
                "kind": "unsatisfied_dependency",
                "gate_id": item["gate_id"],
                "outcome": item["outcome"],
            }
            for item in depends_on
            if item["outcome"] not in {"approved", "waived", "not_required"}
        ]
        current_outcome = "blocked"
    elif "blocked" in decisions:
        blocking_reasons = [
            {
                "kind": "review_decision",
                "decision": "blocked",
            }
        ]
        current_outcome = "blocked"
    elif open_question_reasons or validation_issue_reasons:
        blocking_reasons = open_question_reasons + validation_issue_reasons
        current_outcome = "blocked"
    elif "changes_requested" in decisions:
        blocking_reasons = [
            {
                "kind": "review_decision",
                "decision": "changes_requested",
            }
        ]
        current_outcome = "changes_requested"
    elif missing:
        blocking_reasons = [
            {
                "kind": "missing_approval_capability",
                "capability": capability,
            }
            for capability in missing
        ]
        current_outcome = "blocked"
    else:
        blocking_reasons = []
        current_outcome = "approved"

    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "artifact_version": artifact.header.get("version"),
        "gate_id": policy.gate_id,
        "delivery_stage": policy.delivery_stage,
        "current_outcome": current_outcome,
        "effective_blocking": policy.enforcement == "blocking",
        "required_approval_capabilities": required,
        "satisfied_approval_capabilities": satisfied,
        "missing_approval_capabilities": missing,
        "missing_evidence": list(policy.required_evidence),
        "blocking_reasons": blocking_reasons,
        "decision_sources": decision_sources,
        "depends_on": depends_on,
        "controls_transition": {
            "from_status": policy.controls_transition[0],
            "to_status": policy.controls_transition[1],
        },
        "controlled_transition_allowed": current_outcome == "approved",
    }


def _collect_review_evidence(review_records: object) -> tuple[set[str], list[dict], set[str]]:
    if not isinstance(review_records, list):
        return set(), [], set()

    approval_tokens: set[str] = set()
    decision_sources: list[dict] = []
    decisions: set[str] = set()
    for record in review_records:
        if not isinstance(record, dict):
            continue

        reviewer = record.get("reviewer", {})
        if not isinstance(reviewer, dict):
            continue

        role = reviewer.get("role")
        capability = reviewer.get("capability")
        decision = record.get("decision")
        related_transition = record.get("related_transition")

        if isinstance(decision, str):
            decisions.add(decision)
        if decision == "approve" and related_transition in (None, "in_review->approved"):
            if isinstance(role, str):
                approval_tokens.add(role)
            if isinstance(capability, str):
                approval_tokens.add(capability)

        decision_sources.append(
            {
                "kind": "review_record",
                "decision": decision,
                "actor_id": reviewer.get("actor_id"),
                "role": role,
                "capability": capability,
            }
        )

    return approval_tokens, decision_sources, decisions


def _evaluate_dependencies(
    repository: Repository,
    schema: dict,
    artifact,
    policy: GatePolicy,
    *,
    seen_artifact_ids: set[str],
) -> list[dict]:
    results: list[dict] = []
    for gate_id in policy.depends_on_gates:
        dependency_policy = _POLICY_BY_GATE_ID[gate_id]
        dependency_artifact = _find_dependency_artifact(repository, artifact, dependency_policy.artifact_type)
        if dependency_artifact is None:
            results.append({"gate_id": gate_id, "outcome": "not_required"})
            continue
        if dependency_artifact.artifact_id in seen_artifact_ids:
            results.append({"gate_id": gate_id, "outcome": "blocked"})
            continue
        dependency_payload = _evaluate_artifact_workflow(
            repository,
            schema,
            dependency_artifact.artifact_id,
            seen_artifact_ids=seen_artifact_ids,
        )
        results.append(
            {
                "gate_id": gate_id,
                "outcome": dependency_payload["current_outcome"],
            }
        )
    return results


def _find_dependency_artifact(repository: Repository, artifact, dependency_artifact_type: str):
    feature_key = get_artifact_feature_key(artifact)
    candidates = [
        candidate
        for candidate in repository.artifacts_by_id.values()
        if candidate.artifact_type == dependency_artifact_type
        and get_artifact_feature_key(candidate) == feature_key
    ]
    if not candidates:
        return None

    current_version = artifact.header.get("version")
    if isinstance(current_version, str):
        version_matches = [
            candidate
            for candidate in candidates
            if candidate.header.get("version") == current_version
        ]
        if len(version_matches) == 1:
            return version_matches[0]

    return sorted(candidates, key=lambda candidate: candidate.artifact_id)[0]


def _collect_open_question_reasons(artifact) -> list[dict]:
    open_questions = artifact.header.get("open_questions", [])
    if not isinstance(open_questions, list):
        return []
    return [
        {
            "kind": "open_question",
            "q_id": question.get("q_id"),
            "status": question.get("status"),
            "note": question.get("note"),
        }
        for question in open_questions
        if isinstance(question, dict) and question.get("status") == "open"
    ]


def _collect_validation_issue_reasons(repository: Repository, schema: dict, artifact) -> list[dict]:
    artifact_ids = {artifact.artifact_id}
    unit_ids = {
        unit["id"]
        for unit in artifact.trace_units
        if isinstance(unit, dict) and isinstance(unit.get("id"), str)
    }
    paths = {str(artifact.path)}
    issues = validate_repository(repository, schema)

    scoped = [
        serialize_issue(issue)
        for issue in issues
        if issue.code != "missing_required_review_record"
        and (
            issue.object_id in artifact_ids
            or issue.object_id in unit_ids
            or issue.path in paths
        )
    ]
    return [
        {
            "kind": "validation_issue",
            "code": issue["code"],
            "object_id": issue["object_id"],
            "message": issue["message"],
        }
        for issue in sorted(scoped, key=lambda item: (item["code"], item["object_id"] or ""))
    ]


def _has_unsatisfied_dependency(depends_on: list[dict]) -> bool:
    return any(item["outcome"] not in {"approved", "waived", "not_required"} for item in depends_on)
