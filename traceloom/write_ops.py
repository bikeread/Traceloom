from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile

from traceloom.artifact_io import (
    replace_relation_edges_block,
    write_artifact_document,
    write_artifact_header,
)
from traceloom.defaults import resolve_default_schema_path
from traceloom.draft_templates import render_artifact_scaffold
from traceloom.repository import load_repository
from traceloom.validators import load_schema, validate_repository


DEFAULT_SCHEMA_PATH = resolve_default_schema_path(module_file=__file__)
REVISION_EDITABLE_STATUSES = {"draft", "in_review"}
REVISION_ALLOWED_HEADER_FIELDS = {
    "title",
    "summary",
    "scope",
    "upstream_refs",
    "downstream_refs",
    "reviewers",
    "open_questions",
    "tags",
    "change_summary",
    "external_refs",
}


def create_artifact_draft(
    repo_root: str | Path,
    *,
    relative_path: str,
    artifact_type: str,
    artifact_id: str,
    title: str,
    summary: str,
    version: str,
    owner: dict,
    scope: dict,
    created_at: str,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    repo_root_path = Path(repo_root)
    repository = load_repository([repo_root_path])
    if artifact_id in repository.artifacts_by_id:
        raise ValueError(f"artifact_id '{artifact_id}' already exists")

    target_path = _resolve_repo_relative_path(repo_root_path, relative_path)
    if target_path.exists():
        raise ValueError(f"path '{relative_path}' already exists")

    schema = load_schema(schema_path)
    header = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "title": title,
        "summary": summary,
        "status": "draft",
        "version": version,
        "owner": owner,
        "created_at": created_at,
        "updated_at": created_at,
        "scope": scope,
    }
    body = render_artifact_scaffold(schema, artifact_type)

    with tempfile.TemporaryDirectory() as temp_dir:
        staged_root = Path(temp_dir) / "repo"
        shutil.copytree(repo_root_path, staged_root)
        staged_target = _resolve_repo_relative_path(staged_root, relative_path)
        staged_target.parent.mkdir(parents=True, exist_ok=True)
        write_artifact_document(staged_target, header, body)
        issues = validate_repository(load_repository([staged_root]), schema)

    if issues:
        first_issue = issues[0]
        raise ValueError(f"{first_issue.code}: {first_issue.message}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    write_artifact_document(target_path, header, body)
    return {
        "artifact_id": artifact_id,
        "path": str(target_path),
        "status": "draft",
    }


def revise_artifact_draft(
    repo_root: str | Path,
    *,
    artifact_id: str,
    body: str,
    header_updates: dict | None,
    updated_at: str,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    repository = load_repository([Path(repo_root)])
    artifact = repository.artifacts_by_id.get(artifact_id)
    if artifact is None:
        raise KeyError(f"unknown artifact_id '{artifact_id}'")
    if artifact.status not in REVISION_EDITABLE_STATUSES:
        raise ValueError("only draft or in_review artifacts may be revised in place")

    header = _merge_revision_header_updates(
        artifact.header,
        header_updates=header_updates or {},
        updated_at=updated_at,
    )
    _validate_document_revision(
        Path(repo_root),
        artifact_id=artifact_id,
        header=header,
        body=body,
        schema_path=schema_path,
    )
    write_artifact_document(artifact.path, header, body)
    return {
        "artifact_id": artifact_id,
        "status": artifact.status,
        "path": str(artifact.path),
        "updated_fields": ["body", *sorted((header_updates or {}).keys())],
    }


def supersede_artifact_version(
    repo_root: str | Path,
    *,
    successor_artifact_id: str,
    predecessor_artifact_id: str,
    edge_id: str,
    created_at: str,
    created_by: dict,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    repository = load_repository([Path(repo_root)])
    successor = repository.artifacts_by_id.get(successor_artifact_id)
    if successor is None:
        raise KeyError(f"unknown artifact_id '{successor_artifact_id}'")
    predecessor = repository.artifacts_by_id.get(predecessor_artifact_id)
    if predecessor is None:
        raise KeyError(f"unknown artifact_id '{predecessor_artifact_id}'")
    if successor.status not in REVISION_EDITABLE_STATUSES:
        raise ValueError("only draft or in_review successor artifacts may be superseded in place")

    relation_edges = list(successor.relation_edges)
    relation_edges.append(
        _build_supersedes_edge(
            edge_id=edge_id,
            successor=successor,
            predecessor=predecessor,
            created_at=created_at,
            created_by=created_by,
        )
    )
    body = replace_relation_edges_block(successor.body, relation_edges)
    _validate_document_revision(
        Path(repo_root),
        artifact_id=successor_artifact_id,
        header=successor.header,
        body=body,
        schema_path=schema_path,
    )
    write_artifact_document(successor.path, successor.header, body)
    return {
        "artifact_id": successor_artifact_id,
        "updated_field": "relation_edges",
        "path": str(successor.path),
    }


def record_review_decision(
    repo_root: str | Path,
    *,
    artifact_id: str,
    review_record: dict,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    return _append_artifact_record(
        repo_root,
        artifact_id=artifact_id,
        field_name="review_records",
        record=review_record,
        schema_path=schema_path,
    )


def record_validation_result(
    repo_root: str | Path,
    *,
    artifact_id: str,
    validation_record: dict,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    return _append_artifact_record(
        repo_root,
        artifact_id=artifact_id,
        field_name="validation_records",
        record=validation_record,
        schema_path=schema_path,
    )


def promote_artifact_status(
    repo_root: str | Path,
    *,
    artifact_id: str,
    target_status: str,
    changed_by: dict,
    changed_at: str,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    repository = load_repository([Path(repo_root)])
    artifact = repository.artifacts_by_id.get(artifact_id)
    if artifact is None:
        raise KeyError(f"unknown artifact_id '{artifact_id}'")

    header = _build_promoted_header(
        artifact.header,
        target_status=target_status,
        changed_by=changed_by,
        changed_at=changed_at,
    )
    _validate_promoted_repository(Path(repo_root), artifact_id, header, schema_path)
    write_artifact_header(artifact.path, header)
    return {
        "artifact_id": artifact_id,
        "status": target_status,
        "updated_field": "status",
        "path": str(artifact.path),
    }


def _append_artifact_record(
    repo_root: str | Path,
    *,
    artifact_id: str,
    field_name: str,
    record: dict,
    schema_path: str | Path,
) -> dict:
    repository = load_repository([Path(repo_root)])
    artifact = repository.artifacts_by_id.get(artifact_id)
    if artifact is None:
        raise KeyError(f"unknown artifact_id '{artifact_id}'")

    header = deepcopy(artifact.header)
    existing_records = header.get(field_name, [])
    if not isinstance(existing_records, list):
        raise ValueError(f"{artifact_id} field '{field_name}' must be a list")

    header[field_name] = list(existing_records)
    header[field_name].append(record)

    recorded_at = record.get("recorded_at")
    if isinstance(recorded_at, str):
        header["updated_at"] = recorded_at

    _validate_header_mutation(repository, artifact_id, header, schema_path)
    write_artifact_header(artifact.path, header)
    return {
        "artifact_id": artifact_id,
        "updated_field": field_name,
        "path": str(artifact.path),
    }


def _validate_header_mutation(
    repository,
    artifact_id: str,
    header: dict,
    schema_path: str | Path,
) -> None:
    schema = load_schema(schema_path)
    staged_repository = deepcopy(repository)
    staged_repository.artifacts_by_id[artifact_id].header = header

    artifact_issues = [
        issue
        for issue in validate_repository(staged_repository, schema)
        if issue.object_id == artifact_id
    ]
    if artifact_issues:
        first_issue = artifact_issues[0]
        raise ValueError(f"{first_issue.code}: {first_issue.message}")


def _build_promoted_header(
    current_header: dict,
    *,
    target_status: str,
    changed_by: dict,
    changed_at: str,
) -> dict:
    header = deepcopy(current_header)
    status_history = header.get("status_history", [])
    if not isinstance(status_history, list):
        raise ValueError("status_history must be a list")

    header["status_history"] = list(status_history)
    header["status_history"].append(
        {
            "from_status": current_header.get("status"),
            "to_status": target_status,
            "changed_at": changed_at,
            "changed_by": changed_by,
        }
    )
    header["status"] = target_status
    header["updated_at"] = changed_at
    return header


def _validate_promoted_repository(
    repo_root: Path,
    artifact_id: str,
    header: dict,
    schema_path: str | Path,
) -> None:
    schema = load_schema(schema_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        staged_root = Path(temp_dir) / "repo"
        shutil.copytree(repo_root, staged_root)

        staged_repository = load_repository([staged_root])
        staged_artifact = staged_repository.artifacts_by_id.get(artifact_id)
        if staged_artifact is None:
            raise KeyError(f"unknown artifact_id '{artifact_id}'")

        write_artifact_header(staged_artifact.path, header)
        issues = validate_repository(load_repository([staged_root]), schema)

    if issues:
        first_issue = issues[0]
        raise ValueError(f"{first_issue.code}: {first_issue.message}")


def _validate_document_revision(
    repo_root: Path,
    *,
    artifact_id: str,
    header: dict,
    body: str,
    schema_path: str | Path,
) -> None:
    schema = load_schema(schema_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        staged_root = Path(temp_dir) / "repo"
        shutil.copytree(repo_root, staged_root)

        staged_repository = load_repository([staged_root])
        staged_artifact = staged_repository.artifacts_by_id.get(artifact_id)
        if staged_artifact is None:
            raise KeyError(f"unknown artifact_id '{artifact_id}'")

        write_artifact_document(staged_artifact.path, header, body)
        issues = validate_repository(load_repository([staged_root]), schema)

    if issues:
        first_issue = issues[0]
        raise ValueError(f"{first_issue.code}: {first_issue.message}")


def _merge_revision_header_updates(
    current_header: dict,
    *,
    header_updates: dict,
    updated_at: str,
) -> dict:
    header = deepcopy(current_header)
    for field_name, value in header_updates.items():
        if field_name not in REVISION_ALLOWED_HEADER_FIELDS:
            raise ValueError(f"field '{field_name}' cannot be revised in place")
        header[field_name] = value
    header["updated_at"] = updated_at
    return header


def _build_supersedes_edge(
    *,
    edge_id: str,
    successor,
    predecessor,
    created_at: str,
    created_by: dict,
) -> dict:
    return {
        "edge_id": edge_id,
        "relation_type": "supersedes",
        "from": {
            "id": successor.artifact_id,
            "kind": "artifact",
            "type": successor.artifact_type,
        },
        "to": {
            "id": predecessor.artifact_id,
            "kind": "artifact",
            "type": predecessor.artifact_type,
        },
        "created_at": created_at,
        "created_by": created_by,
    }


def _resolve_repo_relative_path(repo_root: Path, relative_path: str) -> Path:
    resolved_root = repo_root.resolve()
    target_path = (resolved_root / relative_path).resolve()
    try:
        target_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path '{relative_path}' escapes repository root") from exc
    return target_path
