from __future__ import annotations

from traceloom.queries import (
    get_artifact_feature_key,
    get_artifact_target_release,
    list_open_questions,
    trace_downstream,
    trace_upstream,
)
from traceloom.repository import Repository
from traceloom.validators import serialize_issue, validate_repository


FEATURE_READINESS_RULES = (
    ("GOAL", "REQ", "refines"),
    ("REQ", "AC", "refines"),
    ("REQ", "DEC", "covers"),
    ("NFR", "DEC", "covers"),
    ("DEC", "TASK", "implements"),
    ("AC", "TC", "verifies"),
    ("TASK", "REL", "ships"),
    ("REQ", "REL", "ships"),
    ("GOAL", "REV", "evaluates"),
    ("REL", "REV", "evaluates"),
)

RELEASE_READINESS_RULES = (
    ("TASK", "REL", "ships"),
    ("REQ", "REL", "ships"),
    ("GOAL", "REV", "evaluates"),
    ("REL", "REV", "evaluates"),
)

ARTIFACT_FAMILY_ORDER = (
    "brief",
    "prd_story_pack",
    "solution_design",
    "execution_plan",
    "test_acceptance",
    "release_review",
)


def check_feature_readiness(repository: Repository, schema: dict, feature_key: str) -> dict:
    artifacts = _artifacts_for_feature(repository, feature_key)
    readiness_artifacts, baseline_artifact_ids, ambiguous_families = _resolve_readiness_artifacts(repository, artifacts)
    artifact_ids = {artifact.artifact_id for artifact in readiness_artifacts}
    unit_ids = _trace_unit_ids_for_artifacts(readiness_artifacts)
    coverage = _calculate_scoped_coverage(repository, unit_ids, FEATURE_READINESS_RULES)
    issues = _scoped_validation_issues(
        repository,
        schema,
        artifact_ids,
        unit_ids,
        {str(item.path) for item in readiness_artifacts},
    )
    open_questions = list_open_questions(repository)
    feature_questions = [item for item in open_questions if item["artifact_id"] in artifact_ids]
    blockers = _build_blockers(issues, feature_questions)
    artifact_summaries = [_artifact_summary(item) for item in readiness_artifacts]

    return _finalize_readiness_summary({
        "feature_key": feature_key,
        "artifacts": artifact_summaries,
        "baseline_artifact_ids": baseline_artifact_ids,
        "ambiguous_artifact_families": ambiguous_families,
        "artifact_gap_map": _build_artifact_gap_map(
            repository,
            readiness_artifacts,
            coverage,
            issues,
            feature_questions,
            ambiguous_families,
        ),
        "coverage": coverage,
        "open_questions": feature_questions,
        "validation_issues": issues,
        "blockers": blockers,
    })


def check_release_readiness(
    repository: Repository,
    schema: dict,
    *,
    release_target: str | None = None,
    feature_key: str | None = None,
) -> dict:
    artifacts = _artifacts_for_release(repository, release_target=release_target, feature_key=feature_key)
    readiness_artifacts, baseline_artifact_ids, ambiguous_families = _resolve_readiness_artifacts(repository, artifacts)
    artifact_ids = {artifact.artifact_id for artifact in readiness_artifacts}
    unit_ids = _trace_unit_ids_for_artifacts(readiness_artifacts)
    issues = _scoped_validation_issues(
        repository,
        schema,
        artifact_ids,
        unit_ids,
        {str(item.path) for item in readiness_artifacts},
    )
    open_questions = list_open_questions(repository)
    release_questions = [item for item in open_questions if item["artifact_id"] in artifact_ids]
    release_artifact_ids = sorted(
        artifact.artifact_id for artifact in readiness_artifacts if artifact.artifact_type == "release_review"
    )
    blockers = _build_blockers(issues, release_questions)
    artifact_summaries = [_artifact_summary(item) for item in readiness_artifacts]
    resolved_feature_key = feature_key if feature_key is not None else _infer_shared_feature_key(readiness_artifacts)

    return _finalize_readiness_summary({
        "release_target": release_target,
        "feature_key": resolved_feature_key,
        "artifacts": artifact_summaries,
        "baseline_artifact_ids": baseline_artifact_ids,
        "ambiguous_artifact_families": ambiguous_families,
        "release_artifact_ids": release_artifact_ids,
        "coverage": _calculate_scoped_coverage(repository, unit_ids, RELEASE_READINESS_RULES),
        "open_questions": release_questions,
        "validation_issues": issues,
        "blockers": blockers,
    })


def analyze_change_impact(repository: Repository, object_id: str) -> dict:
    if object_id in repository.trace_units_by_id:
        trace_unit_ids = [object_id]
        object_kind = "trace_unit"
        owning_artifact_id = repository.trace_units_by_id[object_id].artifact_id
    elif object_id in repository.artifacts_by_id:
        artifact = repository.artifacts_by_id[object_id]
        trace_unit_ids = sorted(
            unit["id"] for unit in artifact.trace_units if isinstance(unit, dict) and isinstance(unit.get("id"), str)
        )
        object_kind = "artifact"
        owning_artifact_id = object_id
    else:
        raise KeyError(f"unknown object id '{object_id}'")

    seed_unit_ids = set(trace_unit_ids)
    upstream_unit_ids = _trace_many(repository, trace_unit_ids, direction="upstream") - seed_unit_ids
    downstream_unit_ids = _trace_many(repository, trace_unit_ids, direction="downstream") - seed_unit_ids
    direct_upstream_trace_unit_ids, direct_downstream_trace_unit_ids = _direct_trace_context(repository, seed_unit_ids)
    upstream_artifact_ids = _artifact_ids_for_units(repository, upstream_unit_ids)
    downstream_artifact_ids = _artifact_ids_for_units(repository, downstream_unit_ids)
    related_artifact_ids = _artifact_ids_for_units(repository, seed_unit_ids | upstream_unit_ids | downstream_unit_ids)
    related_edges = _direct_edges_for_units(repository, seed_unit_ids)

    return {
        "object_id": object_id,
        "object_kind": object_kind,
        "owning_artifact_id": owning_artifact_id,
        "trace_unit_ids": sorted(seed_unit_ids),
        "direct_downstream_trace_unit_ids": direct_downstream_trace_unit_ids,
        "upstream_trace_unit_ids": sorted(upstream_unit_ids),
        "downstream_trace_unit_ids": sorted(downstream_unit_ids),
        "downstream_artifact_ids": downstream_artifact_ids,
        "direct_upstream_trace_unit_ids": direct_upstream_trace_unit_ids,
        "upstream_artifact_ids": upstream_artifact_ids,
        "related_artifact_ids": related_artifact_ids,
        "related_edges": related_edges,
    }


def _artifact_summary(artifact) -> dict:
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "status": artifact.status,
        "version": artifact.header.get("version"),
        "path": str(artifact.path),
    }


def _artifacts_for_feature(repository: Repository, feature_key: str) -> list:
    artifacts = [
        artifact
        for artifact in repository.artifacts_by_id.values()
        if get_artifact_feature_key(artifact) == feature_key
    ]
    return sorted(artifacts, key=lambda artifact: artifact.artifact_id)


def _artifacts_for_release(
    repository: Repository,
    *,
    release_target: str | None,
    feature_key: str | None,
) -> list:
    artifacts = list(repository.artifacts_by_id.values())
    if release_target is not None:
        artifacts = [artifact for artifact in artifacts if get_artifact_target_release(artifact) == release_target]
    if feature_key is not None:
        artifacts = [artifact for artifact in artifacts if get_artifact_feature_key(artifact) == feature_key]
    return sorted(artifacts, key=lambda artifact: artifact.artifact_id)


def _resolve_readiness_artifacts(repository: Repository, artifacts: list) -> tuple[list, list[str], list[dict]]:
    families: dict[tuple[str | None, str], list] = {}
    for artifact in artifacts:
        family_key = (get_artifact_feature_key(artifact), artifact.artifact_type)
        families.setdefault(family_key, []).append(artifact)

    superseded_targets: dict[tuple[str | None, str], set[str]] = {}
    for edge in repository.relation_edges_by_id.values():
        if edge.get("relation_type") != "supersedes":
            continue
        from_endpoint = edge.get("from", {})
        to_endpoint = edge.get("to", {})
        if from_endpoint.get("kind") != "artifact" or to_endpoint.get("kind") != "artifact":
            continue
        source_id = from_endpoint.get("id")
        target_id = to_endpoint.get("id")
        if source_id not in repository.artifacts_by_id or target_id not in repository.artifacts_by_id:
            continue

        source = repository.artifacts_by_id[source_id]
        target = repository.artifacts_by_id[target_id]
        source_family = (get_artifact_feature_key(source), source.artifact_type)
        target_family = (get_artifact_feature_key(target), target.artifact_type)
        if source_family != target_family:
            continue
        superseded_targets.setdefault(source_family, set()).add(target.artifact_id)

    selected: list = []
    baseline_artifact_ids: list[str] = []
    ambiguous_families: list[dict] = []
    for family_key, family_artifacts in sorted(families.items(), key=lambda item: (item[0][0] or "", item[0][1])):
        ordered_family = sorted(family_artifacts, key=lambda artifact: artifact.artifact_id)
        if len(ordered_family) == 1:
            selected.extend(ordered_family)
            baseline_artifact_ids.append(ordered_family[0].artifact_id)
            continue

        family_superseded_targets = superseded_targets.get(family_key, set())
        candidates = [artifact for artifact in ordered_family if artifact.artifact_id not in family_superseded_targets]
        if len(candidates) == 1:
            selected.extend(candidates)
            baseline_artifact_ids.append(candidates[0].artifact_id)
            continue

        unresolved = candidates if candidates else ordered_family
        selected.extend(unresolved)
        ambiguous_families.append(
            {
                "feature_key": family_key[0],
                "artifact_type": family_key[1],
                "candidate_artifact_ids": [artifact.artifact_id for artifact in unresolved],
            }
        )

    return (
        sorted(selected, key=lambda artifact: artifact.artifact_id),
        sorted(baseline_artifact_ids),
        sorted(
            ambiguous_families,
            key=lambda item: ((item.get("feature_key") or ""), item["artifact_type"]),
        ),
    )


def _infer_shared_feature_key(artifacts: list) -> str | None:
    feature_keys = sorted(
        {
            feature_key
            for artifact in artifacts
            for feature_key in [get_artifact_feature_key(artifact)]
            if feature_key is not None
        }
    )
    if len(feature_keys) == 1:
        return feature_keys[0]
    return None


def _trace_unit_ids_for_artifacts(artifacts: list) -> set[str]:
    return {
        unit["id"]
        for artifact in artifacts
        for unit in artifact.trace_units
        if isinstance(unit, dict) and isinstance(unit.get("id"), str)
    }


def _scoped_validation_issues(
    repository: Repository,
    schema: dict,
    artifact_ids: set[str],
    unit_ids: set[str],
    paths: set[str],
) -> list[dict]:
    issues = validate_repository(repository, schema)
    object_ids = artifact_ids | unit_ids
    scoped = [
        serialize_issue(issue)
        for issue in issues
        if issue.object_id in object_ids or issue.path in paths
    ]
    return sorted(scoped, key=lambda item: (item["code"], item["object_id"] or "", item["message"]))


def _calculate_scoped_coverage(repository: Repository, unit_ids: set[str], rules: tuple[tuple[str, str, str], ...]) -> list[dict]:
    coverage: list[dict] = []
    for upstream_type, downstream_type, relation_type in rules:
        upstream_ids = sorted(
            unit_id
            for unit_id in unit_ids
            if repository.trace_units_by_id[unit_id].unit.get("type") == upstream_type
        )
        covered: set[str] = set()
        for edge in repository.relation_edges_by_id.values():
            if edge.get("relation_type") != relation_type:
                continue
            from_endpoint = edge.get("from", {})
            to_endpoint = edge.get("to", {})
            from_id = from_endpoint.get("id")
            to_id = to_endpoint.get("id")
            if from_id not in unit_ids or to_id not in unit_ids:
                continue
            if from_endpoint.get("type") != upstream_type or to_endpoint.get("type") != downstream_type:
                continue
            covered.add(from_id)
        coverage.append(
            {
                "upstream_type": upstream_type,
                "downstream_type": downstream_type,
                "relation_type": relation_type,
                "covered_ids": sorted(covered),
                "missing_ids": sorted(unit_id for unit_id in upstream_ids if unit_id not in covered),
            }
        )
    return coverage


def _build_artifact_gap_map(
    repository: Repository,
    readiness_artifacts: list,
    coverage: list[dict],
    validation_issues: list[dict],
    open_questions: list[dict],
    ambiguous_families: list[dict],
) -> list[dict]:
    artifact_entries = _initialize_artifact_gap_map_entries(readiness_artifacts)
    path_to_artifact = {str(artifact.path): artifact for artifact in readiness_artifacts}

    for coverage_item in coverage:
        if not coverage_item["missing_ids"]:
            continue
        grouped_missing: dict[str, dict[str, set[str] | list[str]]] = {}
        for unit_id in coverage_item["missing_ids"]:
            if unit_id not in repository.trace_units_by_id:
                continue
            record = repository.trace_units_by_id[unit_id]
            artifact_group = grouped_missing.setdefault(
                record.artifact_type,
                {
                    "missing_ids": set(),
                    "artifact_ids": set(),
                },
            )
            artifact_group["missing_ids"].add(unit_id)
            artifact_group["artifact_ids"].add(record.artifact_id)

        for artifact_type, group in grouped_missing.items():
            artifact_entries.setdefault(artifact_type, _empty_artifact_gap_entry(artifact_type))
            artifact_entries[artifact_type]["blocking_gaps"].append(
                {
                    "kind": "missing_traceability",
                    "rule": {
                        "upstream_type": coverage_item["upstream_type"],
                        "downstream_type": coverage_item["downstream_type"],
                        "relation_type": coverage_item["relation_type"],
                    },
                    "artifact_ids": sorted(group["artifact_ids"]),
                    "missing_ids": sorted(group["missing_ids"]),
                    "trace_chain_hint": (
                        f"{coverage_item['upstream_type']} -> {coverage_item['downstream_type']}"
                    ),
                }
            )

    for issue in validation_issues:
        if issue["code"] == "missing_traceability":
            continue
        artifact_info = _resolve_issue_artifact_info(repository, issue, path_to_artifact)
        if artifact_info is None:
            continue
        artifact_type, artifact_id = artifact_info
        artifact_entries.setdefault(artifact_type, _empty_artifact_gap_entry(artifact_type))
        artifact_entries[artifact_type]["blocking_gaps"].append(
            {
                "kind": "validation_issue",
                "code": issue["code"],
                "artifact_id": artifact_id,
                "object_id": issue["object_id"],
                "message": issue["message"],
            }
        )

    for question in open_questions:
        if question.get("status") != "open":
            continue
        artifact_type = question["artifact_type"]
        artifact_entries.setdefault(artifact_type, _empty_artifact_gap_entry(artifact_type))
        artifact_entries[artifact_type]["attention_items"].append(
            {
                "kind": "open_question",
                "artifact_id": question["artifact_id"],
                "q_id": question["q_id"],
                "status": question["status"],
                "note": question["note"],
            }
        )

    for family in ambiguous_families:
        artifact_type = family["artifact_type"]
        artifact_entries.setdefault(artifact_type, _empty_artifact_gap_entry(artifact_type))
        artifact_entries[artifact_type]["attention_items"].append(
            {
                "kind": "ambiguous_baseline",
                "feature_key": family.get("feature_key"),
                "candidate_artifact_ids": family["candidate_artifact_ids"],
                "message": (
                    f"Multiple candidate baseline artifacts for artifact type '{artifact_type}'"
                ),
            }
        )

    return [
        {
            **entry,
            "blocking_gaps": sorted(
                entry["blocking_gaps"],
                key=lambda item: (
                    item["kind"],
                    item.get("artifact_id", ""),
                    item.get("trace_chain_hint", ""),
                    item.get("code", ""),
                ),
            ),
            "attention_items": sorted(
                entry["attention_items"],
                key=lambda item: (
                    item["kind"],
                    item.get("artifact_id", ""),
                    item.get("q_id", ""),
                ),
            ),
        }
        for _, entry in sorted(
            artifact_entries.items(),
            key=lambda item: _artifact_family_sort_key(item[0]),
        )
    ]


def _initialize_artifact_gap_map_entries(readiness_artifacts: list) -> dict[str, dict]:
    grouped_artifact_ids: dict[str, list[str]] = {}
    for artifact in readiness_artifacts:
        grouped_artifact_ids.setdefault(artifact.artifact_type, []).append(artifact.artifact_id)
    return {
        artifact_type: {
            "artifact_type": artifact_type,
            "artifact_ids": sorted(artifact_ids),
            "blocking_gaps": [],
            "attention_items": [],
        }
        for artifact_type, artifact_ids in grouped_artifact_ids.items()
    }


def _empty_artifact_gap_entry(artifact_type: str) -> dict:
    return {
        "artifact_type": artifact_type,
        "artifact_ids": [],
        "blocking_gaps": [],
        "attention_items": [],
    }


def _resolve_issue_artifact_info(
    repository: Repository,
    issue: dict,
    path_to_artifact: dict[str, object],
) -> tuple[str, str] | None:
    object_id = issue.get("object_id")
    if isinstance(object_id, str):
        if object_id in repository.artifacts_by_id:
            artifact = repository.artifacts_by_id[object_id]
            return artifact.artifact_type, artifact.artifact_id
        if object_id in repository.trace_units_by_id:
            record = repository.trace_units_by_id[object_id]
            return record.artifact_type, record.artifact_id

    path = issue.get("path")
    if isinstance(path, str) and path in path_to_artifact:
        artifact = path_to_artifact[path]
        return artifact.artifact_type, artifact.artifact_id

    return None


def _artifact_family_sort_key(artifact_type: str) -> tuple[int, str]:
    if artifact_type in ARTIFACT_FAMILY_ORDER:
        return (ARTIFACT_FAMILY_ORDER.index(artifact_type), artifact_type)
    return (len(ARTIFACT_FAMILY_ORDER), artifact_type)


def _build_blockers(validation_issues: list[dict], open_questions: list[dict]) -> list[dict]:
    blockers = [
        {"kind": "validation_issue", **issue}
        for issue in validation_issues
    ]
    blockers.extend(
        {
            "kind": "open_question",
            "artifact_id": question["artifact_id"],
            "artifact_type": question["artifact_type"],
            "q_id": question["q_id"],
            "status": question["status"],
            "note": question["note"],
        }
        for question in open_questions
        if question.get("status") == "open"
    )
    return sorted(blockers, key=lambda item: (item["kind"], item.get("artifact_id", ""), item.get("q_id", "")))


def _finalize_readiness_summary(summary: dict) -> dict:
    artifacts = summary.get("artifacts", [])
    validation_issues = summary.get("validation_issues", [])
    open_questions = summary.get("open_questions", [])
    blockers = summary.get("blockers", [])
    summary["artifact_ids"] = [artifact["artifact_id"] for artifact in artifacts]
    summary.setdefault("baseline_artifact_ids", list(summary["artifact_ids"]))
    summary.setdefault("ambiguous_artifact_families", [])
    summary["blocking_validation_issue_count"] = len(validation_issues)
    summary["open_question_count"] = sum(1 for question in open_questions if question.get("status") == "open")
    summary["blocker_count"] = len(blockers)
    summary["ready"] = not blockers
    return summary


def _trace_many(repository: Repository, trace_unit_ids: list[str], *, direction: str) -> set[str]:
    traced: set[str] = set()
    for trace_unit_id in trace_unit_ids:
        if direction == "upstream":
            traced.update(trace_upstream(repository, trace_unit_id))
        else:
            traced.update(trace_downstream(repository, trace_unit_id))
    return traced


def _direct_trace_context(repository: Repository, unit_ids: set[str]) -> tuple[list[str], list[str]]:
    upstream_ids: set[str] = set()
    downstream_ids: set[str] = set()

    for edge in repository.relation_edges_by_id.values():
        from_endpoint = edge.get("from", {})
        to_endpoint = edge.get("to", {})
        from_id = from_endpoint.get("id")
        to_id = to_endpoint.get("id")
        if from_endpoint.get("kind") != "trace_unit" or to_endpoint.get("kind") != "trace_unit":
            continue
        if isinstance(to_id, str) and to_id in unit_ids and isinstance(from_id, str) and from_id not in unit_ids:
            upstream_ids.add(from_id)
        if isinstance(from_id, str) and from_id in unit_ids and isinstance(to_id, str) and to_id not in unit_ids:
            downstream_ids.add(to_id)

    return sorted(upstream_ids), sorted(downstream_ids)


def _artifact_ids_for_units(repository: Repository, unit_ids: set[str]) -> list[str]:
    return sorted(
        {
            repository.trace_units_by_id[unit_id].artifact_id
            for unit_id in unit_ids
            if unit_id in repository.trace_units_by_id
        }
    )


def _direct_edges_for_units(repository: Repository, unit_ids: set[str]) -> list[dict]:
    edges = [
        edge
        for edge in repository.relation_edges_by_id.values()
        if edge.get("from", {}).get("id") in unit_ids or edge.get("to", {}).get("id") in unit_ids
    ]
    return sorted(edges, key=lambda item: item["edge_id"])
