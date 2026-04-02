from __future__ import annotations

from pathlib import Path
import re

from traceloom.repository import Repository


def get_artifact(repository: Repository, artifact_id: str, *, view: str = "full") -> dict:
    artifact = repository.artifacts_by_id[artifact_id]
    if view == "header":
        return {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "path": str(artifact.path),
            "header": artifact.header,
        }
    if view == "trace_only":
        return {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "path": str(artifact.path),
            "trace_units": artifact.trace_units,
            "relation_edges": artifact.relation_edges,
        }
    if view != "full":
        raise ValueError(f"unsupported artifact view '{view}'")
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "path": str(artifact.path),
        "header": artifact.header,
        "headings": artifact.headings,
        "body": artifact.body,
        "trace_units": artifact.trace_units,
        "relation_edges": artifact.relation_edges,
    }


def get_trace_unit(repository: Repository, trace_unit_id: str) -> dict:
    record = repository.trace_units_by_id[trace_unit_id]
    artifact = repository.artifacts_by_id[record.artifact_id]
    return {
        "trace_unit_id": trace_unit_id,
        "artifact_id": record.artifact_id,
        "artifact_type": record.artifact_type,
        "artifact_path": str(artifact.path),
        "unit": record.unit,
    }


def list_related(
    repository: Repository,
    object_id: str,
    *,
    direction: str = "both",
    relation_type: str | None = None,
) -> list[dict]:
    related: list[dict] = []
    for edge in repository.relation_edges_by_id.values():
        if relation_type is not None and edge.get("relation_type") != relation_type:
            continue

        from_id = edge.get("from", {}).get("id")
        to_id = edge.get("to", {}).get("id")
        if direction in {"both", "downstream"} and from_id == object_id:
            related.append(
                {
                    "edge_id": edge["edge_id"],
                    "relation_type": edge["relation_type"],
                    "direction": "downstream",
                    "related_id": to_id,
                    "from": edge.get("from", {}),
                    "to": edge.get("to", {}),
                }
            )
        if direction in {"both", "upstream"} and to_id == object_id:
            related.append(
                {
                    "edge_id": edge["edge_id"],
                    "relation_type": edge["relation_type"],
                    "direction": "upstream",
                    "related_id": from_id,
                    "from": edge.get("from", {}),
                    "to": edge.get("to", {}),
                }
            )
    return sorted(related, key=lambda item: (item["direction"], item["relation_type"], item["related_id"]))


def trace_upstream(repository: Repository, trace_unit_id: str, *, stop_at_type: str | None = None) -> list[str]:
    return _trace_units(repository, trace_unit_id, direction="upstream", stop_at_type=stop_at_type)


def trace_downstream(repository: Repository, trace_unit_id: str, *, stop_at_type: str | None = None) -> list[str]:
    return _trace_units(repository, trace_unit_id, direction="downstream", stop_at_type=stop_at_type)


def get_status_history(repository: Repository, artifact_id: str) -> list[dict]:
    artifact = repository.artifacts_by_id[artifact_id]
    history = artifact.header.get("status_history", [])
    if not isinstance(history, list):
        return []
    return history


def list_open_questions(
    repository: Repository,
    *,
    artifact_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    questions: list[dict] = []
    artifacts = repository.artifacts_by_id.values()
    if artifact_id is not None:
        artifacts = [repository.artifacts_by_id[artifact_id]]

    for artifact in artifacts:
        open_questions = artifact.header.get("open_questions", [])
        if not isinstance(open_questions, list):
            continue
        for question in open_questions:
            if not isinstance(question, dict):
                continue
            question_status = question.get("status")
            if status is not None and question_status != status:
                continue
            questions.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "artifact_type": artifact.artifact_type,
                    "q_id": question.get("q_id"),
                    "status": question_status,
                    "note": question.get("note"),
                }
            )

    return sorted(questions, key=lambda item: (item["artifact_id"], item["q_id"] or ""))


def list_artifact_versions(repository: Repository, artifact_id: str) -> list[dict]:
    artifact = repository.artifacts_by_id[artifact_id]
    family = _find_artifact_family(repository, artifact)
    return [
        {
            "artifact_id": item.artifact_id,
            "artifact_type": item.artifact_type,
            "version": item.header.get("version"),
            "status": item.status,
            "path": str(item.path),
        }
        for item in family
    ]


def diff_versions(repository: Repository, artifact_id: str, from_version: str, to_version: str) -> dict:
    artifact = repository.artifacts_by_id[artifact_id]
    family = _find_artifact_family(repository, artifact)
    from_artifact = _find_family_artifact_by_version(family, from_version)
    to_artifact = _find_family_artifact_by_version(family, to_version)

    from_header = dict(from_artifact.header)
    to_header = dict(to_artifact.header)
    changed_header_fields = sorted(
        key
        for key in set(from_header) | set(to_header)
        if from_header.get(key) != to_header.get(key)
    )

    from_units = {unit["id"]: unit for unit in from_artifact.trace_units if isinstance(unit, dict) and "id" in unit}
    to_units = {unit["id"]: unit for unit in to_artifact.trace_units if isinstance(unit, dict) and "id" in unit}
    changed_trace_unit_ids = sorted(
        unit_id
        for unit_id in set(from_units) | set(to_units)
        if from_units.get(unit_id) != to_units.get(unit_id)
    )

    from_edges = {
        edge["edge_id"]: edge
        for edge in from_artifact.relation_edges
        if isinstance(edge, dict) and "edge_id" in edge
    }
    to_edges = {
        edge["edge_id"]: edge
        for edge in to_artifact.relation_edges
        if isinstance(edge, dict) and "edge_id" in edge
    }
    changed_relation_edge_ids = sorted(
        edge_id
        for edge_id in set(from_edges) | set(to_edges)
        if from_edges.get(edge_id) != to_edges.get(edge_id)
    )

    return {
        "artifact_type": artifact.artifact_type,
        "from_artifact_id": from_artifact.artifact_id,
        "to_artifact_id": to_artifact.artifact_id,
        "from_version": from_version,
        "to_version": to_version,
        "changed_header_fields": changed_header_fields,
        "changed_trace_unit_ids": changed_trace_unit_ids,
        "changed_relation_edge_ids": changed_relation_edge_ids,
        "body_changed": from_artifact.body != to_artifact.body,
    }


def _trace_units(repository: Repository, trace_unit_id: str, *, direction: str, stop_at_type: str | None) -> list[str]:
    seen = {trace_unit_id}
    queue = [trace_unit_id]

    while queue:
        current = queue.pop(0)
        current_record = repository.trace_units_by_id.get(current)
        current_type = None if current_record is None else current_record.unit.get("type")
        if current != trace_unit_id and stop_at_type is not None and current_type == stop_at_type:
            continue

        for edge in repository.relation_edges_by_id.values():
            from_id = edge.get("from", {}).get("id")
            to_id = edge.get("to", {}).get("id")

            if direction == "downstream" and from_id == current and to_id not in seen:
                seen.add(to_id)
                queue.append(to_id)
            if direction == "upstream" and to_id == current and from_id not in seen:
                seen.add(from_id)
                queue.append(from_id)

    return sorted(seen)


def _find_artifact_family(repository: Repository, artifact) -> list:
    feature_key = _get_artifact_feature_key(artifact.header)
    family = [
        candidate
        for candidate in repository.artifacts_by_id.values()
        if candidate.artifact_type == artifact.artifact_type
        and _get_artifact_feature_key(candidate.header) == feature_key
    ]
    return sorted(family, key=lambda item: _version_sort_key(item.header.get("version")))


def _find_family_artifact_by_version(family: list, version: str):
    for artifact in family:
        if artifact.header.get("version") == version:
            return artifact
    raise KeyError(f"artifact family has no version '{version}'")


def get_artifact_feature_key(artifact) -> str | None:
    return _get_artifact_feature_key(artifact.header)


def get_artifact_target_release(artifact) -> str | None:
    scope = artifact.header.get("scope")
    if not isinstance(scope, dict):
        return None
    target_release = scope.get("target_release")
    if isinstance(target_release, str):
        return target_release
    return None


def _get_artifact_feature_key(header: dict) -> str | None:
    scope = header.get("scope")
    if not isinstance(scope, dict):
        return None
    feature_key = scope.get("feature_key")
    if isinstance(feature_key, str):
        return feature_key
    return None


def _version_sort_key(value: object) -> tuple:
    if not isinstance(value, str):
        return (value,)
    parts = re.findall(r"\d+|[A-Za-z]+", value)
    if not parts:
        return (value,)
    normalized: list[object] = []
    for part in parts:
        if part.isdigit():
            normalized.append(int(part))
        else:
            normalized.append(part.lower())
    return tuple(normalized)
