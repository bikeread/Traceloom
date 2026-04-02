from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess

import yaml

from traceloom.parser import parse_artifact_text
from traceloom.repository import Repository


STATUS_AWARE_TRACEABILITY_GATES = (
    {
        "artifact_type": "prd_story_pack",
        "minimum_status": "in_review",
        "rules": (
            ("GOAL", "REQ", "refines"),
            ("REQ", "AC", "refines"),
        ),
    },
    {
        "artifact_type": "solution_design",
        "minimum_status": "in_review",
        "rules": (
            ("REQ", "DEC", "covers"),
            ("NFR", "DEC", "covers"),
        ),
    },
    {
        "artifact_type": "execution_plan",
        "minimum_status": "in_review",
        "rules": (
            ("DEC", "TASK", "implements"),
        ),
    },
    {
        "artifact_type": "test_acceptance",
        "minimum_status": "approved",
        "rules": (
            ("AC", "TC", "verifies"),
        ),
    },
    {
        "artifact_type": "release_review",
        "minimum_status": "active",
        "rules": (
            ("TASK", "REL", "ships"),
            ("REQ", "REL", "ships"),
            ("GOAL", "REV", "evaluates"),
            ("REL", "REV", "evaluates"),
        ),
    },
)

_GIT_LOOKUP_TIMEOUT_SECONDS = 5


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    object_id: str | None = None
    path: str | None = None


def serialize_issue(issue: ValidationIssue) -> dict:
    return {
        "code": issue.code,
        "message": issue.message,
        "object_id": issue.object_id,
        "path": issue.path,
    }


def load_schema(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_repository(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_validate_duplicates(repository))
    issues.extend(_validate_artifacts(repository, schema))
    issues.extend(_validate_artifact_governance(repository, schema))
    issues.extend(_validate_trace_units(repository, schema))
    issues.extend(_validate_relation_edges(repository, schema))
    issues.extend(_validate_typed_refs(repository))
    issues.extend(_validate_mandatory_traceability(repository, schema))
    return issues


def calculate_coverage(
    repository: Repository,
    upstream_type: str,
    downstream_type: str,
    relation_type: str | None = None,
) -> dict[str, list[str]]:
    covered: set[str] = set()
    for edge in repository.relation_edges_by_id.values():
        from_endpoint = edge.get("from", {})
        to_endpoint = edge.get("to", {})
        if relation_type is not None and edge.get("relation_type") != relation_type:
            continue
        if from_endpoint.get("type") == upstream_type and to_endpoint.get("type") == downstream_type:
            covered.add(from_endpoint["id"])

    upstream_ids = sorted(
        unit_id
        for unit_id, record in repository.trace_units_by_id.items()
        if record.unit.get("type") == upstream_type
    )
    missing = sorted(unit_id for unit_id in upstream_ids if unit_id not in covered)
    return {
        "covered": sorted(covered),
        "missing": missing,
    }


def trace_related_units(repository: Repository, trace_unit_id: str, direction: str = "both") -> list[str]:
    seen = {trace_unit_id}
    queue = [trace_unit_id]

    while queue:
        current = queue.pop(0)
        for edge in repository.relation_edges_by_id.values():
            from_id = edge.get("from", {}).get("id")
            to_id = edge.get("to", {}).get("id")

            if direction in {"both", "downstream"} and from_id == current and to_id not in seen:
                seen.add(to_id)
                queue.append(to_id)

            if direction in {"both", "upstream"} and to_id == current and from_id not in seen:
                seen.add(from_id)
                queue.append(from_id)

    return sorted(seen)


def _validate_duplicates(repository: Repository) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for artifact_id in repository.duplicate_artifact_ids:
        issues.append(
            ValidationIssue("duplicate_artifact_id", f"Duplicate artifact_id found: {artifact_id}", artifact_id)
        )
    for unit_id in repository.duplicate_trace_unit_ids:
        issues.append(
            ValidationIssue("duplicate_trace_unit_id", f"Duplicate trace unit id found: {unit_id}", unit_id)
        )
    for edge_id in repository.duplicate_relation_edge_ids:
        issues.append(
            ValidationIssue("duplicate_relation_edge_id", f"Duplicate relation edge id found: {edge_id}", edge_id)
        )
    return issues


def _validate_artifacts(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    artifact_types = set(schema["common_enums"]["artifact_types"])
    artifact_schema = schema["common_artifact_schema"]

    for artifact in repository.artifacts_by_id.values():
        issues.extend(
            _validate_object_against_schema(
                artifact.header,
                artifact_schema,
                schema,
                object_label=f"{artifact.artifact_id} header",
                object_id=artifact.artifact_id,
                path=str(artifact.path),
            )
        )

        if artifact.artifact_type not in artifact_types:
            continue

        required_sections = _flatten_required_sections(
            schema["artifacts"][artifact.artifact_type]["required_content_sections"]
        )
        normalized_headings = {_normalize_name(name) for name in artifact.headings}
        for section_name in required_sections:
            if section_name not in normalized_headings:
                issues.append(
                    ValidationIssue(
                        "missing_required_section",
                        f"{artifact.artifact_id} is missing required section '{section_name}'",
                        artifact.artifact_id,
                        str(artifact.path),
                    )
                )

        required_trace_units = schema["artifacts"][artifact.artifact_type].get("required_trace_units", {})
        counts: dict[str, int] = {}
        for unit in artifact.trace_units:
            unit_type = unit.get("type")
            if unit_type is None:
                continue
            counts[unit_type] = counts.get(unit_type, 0) + 1
        if artifact.status == "draft":
            continue
        for unit_type, rule in required_trace_units.items():
            minimum = rule.get("minimum", 0)
            if counts.get(unit_type, 0) < minimum:
                issues.append(
                    ValidationIssue(
                        "missing_required_trace_units",
                        f"{artifact.artifact_id} requires at least {minimum} {unit_type} trace unit(s)",
                        artifact.artifact_id,
                        str(artifact.path),
                    )
                )

    return issues


def _validate_trace_units(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    trace_unit_schema = schema["common_trace_unit_schema"]
    trace_unit_type_definitions = schema["trace_unit_type_definitions"]

    for unit_id, record in repository.trace_units_by_id.items():
        unit = record.unit
        artifact_path = str(repository.artifacts_by_id[record.artifact_id].path)
        object_label = f"{unit_id} trace unit"
        issues.extend(
            _validate_object_against_schema(
                unit,
                trace_unit_schema,
                schema,
                object_label=object_label,
                object_id=unit_id,
                path=artifact_path,
            )
        )

        type_definition = trace_unit_type_definitions.get(unit.get("type"))
        if not isinstance(type_definition, dict):
            continue
        for field_name in type_definition.get("required_fields", []):
            if unit.get(field_name) in (None, "", []):
                issues.append(
                    ValidationIssue(
                        "missing_required_field",
                        f"{object_label} is missing required field '{field_name}'",
                        unit_id,
                        artifact_path,
                    )
                )

    return issues


def _validate_artifact_governance(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    status_rank = _build_status_rank(schema)
    state_machines = schema.get("artifact_state_machines", {})

    issues.extend(_validate_immutable_version_lineage(repository, schema))
    issues.extend(_validate_git_immutable_mutations(repository, schema))

    for artifact in repository.artifacts_by_id.values():
        state_machine = state_machines.get(artifact.artifact_type)
        if not isinstance(state_machine, dict):
            continue
        issues.extend(_validate_status_transition_history(artifact, state_machine))
        issues.extend(_validate_required_review_records(artifact, state_machine, status_rank))
        issues.extend(_validate_status_history(artifact, status_rank))

    return issues


def _validate_relation_edges(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for edge_id, edge in repository.relation_edges_by_id.items():
        issues.extend(
            _validate_object_against_schema(
                edge,
                schema["relation_edge_schema"],
                schema,
                object_label=f"{edge_id} relation edge",
                object_id=edge_id,
                path=None,
            )
        )
        for side in ("from", "to"):
            endpoint = edge.get(side, {})
            kind = endpoint.get("kind")
            endpoint_id = endpoint.get("id")
            if kind == "trace_unit" and endpoint_id not in repository.trace_units_by_id:
                issues.append(
                    ValidationIssue(
                        "unresolved_relation_endpoint",
                        f"{edge_id} references missing trace unit '{endpoint_id}'",
                        edge_id,
                    )
                )
            if kind == "trace_unit" and endpoint_id in repository.trace_units_by_id:
                trace_unit_record = repository.trace_units_by_id[endpoint_id]
                endpoint_type = endpoint.get("type")
                endpoint_artifact_id = endpoint.get("artifact_id")
                actual_type = trace_unit_record.unit.get("type")
                actual_artifact_id = trace_unit_record.artifact_id
                if endpoint_type is not None and endpoint_type != actual_type:
                    issues.append(
                        ValidationIssue(
                            "relation_endpoint_type_mismatch",
                            f"{edge_id} {side}.type '{endpoint_type}' does not match trace unit '{endpoint_id}' type '{actual_type}'",
                            edge_id,
                        )
                    )
                if endpoint_artifact_id is not None and endpoint_artifact_id != actual_artifact_id:
                    issues.append(
                        ValidationIssue(
                            "relation_endpoint_artifact_mismatch",
                            f"{edge_id} {side}.artifact_id '{endpoint_artifact_id}' does not match trace unit '{endpoint_id}' artifact_id '{actual_artifact_id}'",
                            edge_id,
                        )
                    )
            if kind == "artifact" and endpoint_id not in repository.artifacts_by_id:
                issues.append(
                    ValidationIssue(
                        "unresolved_relation_endpoint",
                        f"{edge_id} references missing artifact '{endpoint_id}'",
                        edge_id,
                    )
                )
            if kind == "artifact" and endpoint_id in repository.artifacts_by_id:
                artifact = repository.artifacts_by_id[endpoint_id]
                endpoint_type = endpoint.get("type")
                if endpoint_type is not None and endpoint_type != artifact.artifact_type:
                    issues.append(
                        ValidationIssue(
                            "relation_endpoint_type_mismatch",
                            f"{edge_id} {side}.type '{endpoint_type}' does not match artifact '{endpoint_id}' type '{artifact.artifact_type}'",
                            edge_id,
                        )
                    )
    return issues


def _validate_typed_refs(repository: Repository) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for artifact in repository.artifacts_by_id.values():
        for field_name in ("upstream_refs", "downstream_refs"):
            refs = artifact.header.get(field_name, [])
            if not isinstance(refs, list):
                continue
            for index, reference in enumerate(refs):
                issues.extend(
                    _validate_typed_ref_target(
                        repository,
                        reference,
                        source_label=f"{artifact.artifact_id} header.{field_name}[{index}]",
                        object_id=artifact.artifact_id,
                        path=str(artifact.path),
                    )
                )

        for unit in artifact.trace_units:
            unit_id = unit.get("id", artifact.artifact_id)
            for field_name in ("upstream_refs", "downstream_refs"):
                refs = unit.get(field_name, [])
                if not isinstance(refs, list):
                    continue
                for index, reference in enumerate(refs):
                    issues.extend(
                        _validate_typed_ref_target(
                            repository,
                            reference,
                            source_label=f"{unit_id} {field_name}[{index}]",
                            object_id=unit_id,
                            path=str(artifact.path),
                        )
                    )
    return issues


def _validate_mandatory_traceability(repository: Repository, schema: dict) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    status_rank = _build_status_rank(schema)
    for feature_key, gate in _iter_active_traceability_gates(repository, status_rank):
        for upstream_type, downstream_type, relation_type in gate["rules"]:
            coverage = _calculate_scope_coverage(
                repository,
                feature_key=feature_key,
                upstream_type=upstream_type,
                downstream_type=downstream_type,
                relation_type=relation_type,
            )
            for missing_id in coverage["missing"]:
                record = repository.trace_units_by_id[missing_id]
                issues.append(
                    ValidationIssue(
                        "missing_traceability",
                        f"{missing_id} ({upstream_type}) has no {relation_type} link to any {downstream_type} within scope '{feature_key}'",
                        missing_id,
                        str(repository.artifacts_by_id[record.artifact_id].path),
                    )
                )
    return issues


def _flatten_required_sections(value: list | dict) -> list[str]:
    if isinstance(value, list):
        return [_normalize_name(item) for item in value]

    flattened: list[str] = []
    for key, nested in value.items():
        flattened.append(_normalize_name(key))
        if isinstance(nested, list):
            flattened.extend(_normalize_name(item) for item in nested)
    return flattened


def _normalize_name(name: str) -> str:
    lowered = name.replace("_", " ").lower()
    stripped = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    return stripped


def _validate_object_against_schema(
    value: object,
    schema_definition: dict,
    schema: dict,
    *,
    object_label: str,
    object_id: str | None,
    path: str | None,
) -> list[ValidationIssue]:
    if not isinstance(value, dict):
        return [
            ValidationIssue(
                "invalid_field_type",
                f"{object_label} must be an object",
                object_id,
                path,
            )
        ]

    issues: list[ValidationIssue] = []
    required_fields = schema_definition.get("required_fields", [])
    field_definitions = schema_definition.get("field_definitions", {})

    for field_name in required_fields:
        if value.get(field_name) in (None, "", []):
            issues.append(
                ValidationIssue(
                    "missing_required_field",
                    f"{object_label} is missing required field '{field_name}'",
                    object_id,
                    path,
                )
            )

    for field_name, field_value in value.items():
        field_definition = field_definitions.get(field_name)
        if field_definition is None:
            continue
        issues.extend(
            _validate_field_value(
                field_value,
                field_definition,
                schema,
                field_label=f"{object_label}.{field_name}",
                object_id=object_id,
                path=path,
            )
        )

    return issues


def _validate_field_value(
    value: object,
    field_definition: dict,
    schema: dict,
    *,
    field_label: str,
    object_id: str | None,
    path: str | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    field_type = field_definition.get("type")

    if field_type == "string":
        if not isinstance(value, str):
            issues.append(
                ValidationIssue(
                    "invalid_field_type",
                    f"{field_label} must be string",
                    object_id,
                    path,
                )
            )
    elif field_type == "boolean":
        if not isinstance(value, bool):
            issues.append(
                ValidationIssue(
                    "invalid_field_type",
                    f"{field_label} must be boolean",
                    object_id,
                    path,
                )
            )
    elif field_type == "iso8601_datetime":
        if not isinstance(value, str) or not _is_iso8601_datetime(value):
            issues.append(
                ValidationIssue(
                    "invalid_datetime",
                    f"{field_label} must be iso8601_datetime",
                    object_id,
                    path,
                )
            )
        return issues
    elif field_type == "enum":
        allowed_values = _resolve_allowed_values(schema, field_definition)
        if not isinstance(value, str) or value not in allowed_values:
            issues.append(
                ValidationIssue(
                    "invalid_enum_value",
                    f"{field_label} has invalid value '{value}'; expected one of {sorted(allowed_values)}",
                    object_id,
                    path,
                )
            )
        return issues
    elif isinstance(field_type, str) and field_type.startswith("list[") and field_type.endswith("]"):
        item_type = field_type[5:-1]
        if not isinstance(value, list):
            issues.append(
                ValidationIssue(
                    "invalid_field_type",
                    f"{field_label} must be {field_type}",
                    object_id,
                    path,
                )
            )
            return issues
        for index, item in enumerate(value):
            issues.extend(
                _validate_list_item(
                    item,
                    item_type,
                    schema,
                    field_label=f"{field_label}[{index}]",
                    object_id=object_id,
                    path=path,
                )
            )
        return issues
    else:
        nested_schema_definition = _resolve_nested_schema_definition(schema, field_type)
        if nested_schema_definition is not None:
            return _validate_object_against_schema(
                value,
                nested_schema_definition,
                schema,
                object_label=field_label,
                object_id=object_id,
                path=path,
            )
        return issues

    pattern = field_definition.get("pattern")
    if pattern is not None and isinstance(value, str) and re.fullmatch(pattern, value) is None:
        issues.append(
            ValidationIssue(
                "invalid_pattern",
                f"{field_label} value '{value}' does not match pattern '{pattern}'",
                object_id,
                path,
            )
        )
    return issues


def _validate_list_item(
    value: object,
    item_type: str,
    schema: dict,
    *,
    field_label: str,
    object_id: str | None,
    path: str | None,
) -> list[ValidationIssue]:
    if item_type == "string":
        if isinstance(value, str):
            return []
        return [
            ValidationIssue(
                "invalid_field_type",
                f"{field_label} must be string",
                object_id,
                path,
            )
        ]

    nested_schema_definition = _resolve_nested_schema_definition(schema, item_type)
    if nested_schema_definition is None:
        return []
    return _validate_object_against_schema(
        value,
        nested_schema_definition,
        schema,
        object_label=field_label,
        object_id=object_id,
        path=path,
    )


def _resolve_nested_schema_definition(schema: dict, field_type: object) -> dict | None:
    if not isinstance(field_type, str):
        return None
    if field_type in schema.get("supporting_schemas", {}):
        return schema["supporting_schemas"][field_type]
    if field_type == "relation_endpoint":
        return schema["relation_edge_schema"]["relation_endpoint"]
    return None


def _resolve_allowed_values(schema: dict, field_definition: dict) -> set[str]:
    if "allowed_values" in field_definition:
        return set(field_definition["allowed_values"])

    reference = field_definition.get("allowed_values_ref")
    if reference is None:
        return set()

    target: object = schema
    for part in reference.split("."):
        if not isinstance(target, dict):
            return set()
        target = target.get(part)

    if isinstance(target, list):
        return {str(item) for item in target}
    if isinstance(target, dict):
        return {str(key) for key in target.keys()}
    return set()


def _is_iso8601_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_typed_ref_target(
    repository: Repository,
    reference: object,
    *,
    source_label: str,
    object_id: str | None,
    path: str | None,
) -> list[ValidationIssue]:
    if not isinstance(reference, dict):
        return []

    issues: list[ValidationIssue] = []
    target_kind = reference.get("target_kind")
    target_id = reference.get("target_id")
    target_type = reference.get("target_type")
    target_artifact_id = reference.get("target_artifact_id")

    if target_kind == "artifact":
        artifact = repository.artifacts_by_id.get(target_id)
        if artifact is None:
            issues.append(
                ValidationIssue(
                    "unresolved_typed_ref",
                    f"{source_label} references missing artifact '{target_id}'",
                    object_id,
                    path,
                )
            )
            return issues
        if target_type is not None and target_type != artifact.artifact_type:
            issues.append(
                ValidationIssue(
                    "typed_ref_target_type_mismatch",
                    f"{source_label} target_type '{target_type}' does not match artifact '{target_id}' type '{artifact.artifact_type}'",
                    object_id,
                    path,
                )
            )
        return issues

    if target_kind == "trace_unit":
        trace_unit_record = repository.trace_units_by_id.get(target_id)
        if trace_unit_record is None:
            issues.append(
                ValidationIssue(
                    "unresolved_typed_ref",
                    f"{source_label} references missing trace unit '{target_id}'",
                    object_id,
                    path,
                )
            )
            return issues
        actual_type = trace_unit_record.unit.get("type")
        actual_artifact_id = trace_unit_record.artifact_id
        if target_type is not None and target_type != actual_type:
            issues.append(
                ValidationIssue(
                    "typed_ref_target_type_mismatch",
                    f"{source_label} target_type '{target_type}' does not match trace unit '{target_id}' type '{actual_type}'",
                    object_id,
                    path,
                )
            )
        if target_artifact_id is not None and target_artifact_id != actual_artifact_id:
            issues.append(
                ValidationIssue(
                    "typed_ref_target_artifact_mismatch",
                    f"{source_label} target_artifact_id '{target_artifact_id}' does not match trace unit '{target_id}' artifact_id '{actual_artifact_id}'",
                    object_id,
                    path,
                )
            )

    return issues


def _build_status_rank(schema: dict) -> dict[str, int]:
    return {
        status: index
        for index, status in enumerate(schema["common_enums"]["artifact_statuses"])
    }


def _validate_immutable_version_lineage(repository: Repository, schema: dict) -> list[ValidationIssue]:
    state_model = schema.get("state_model", {})
    immutable_statuses = {
        status
        for status in state_model.get("immutable_statuses", [])
        if isinstance(status, str)
    }
    editable_statuses = {
        status for status in state_model.get("editable_statuses", []) if isinstance(status, str)
    }
    if not immutable_statuses:
        return []

    artifact_families: dict[tuple[str, str], list] = {}
    for artifact in repository.artifacts_by_id.values():
        feature_key = _get_artifact_feature_key(artifact.header)
        if feature_key is None:
            continue
        artifact_families.setdefault((feature_key, artifact.artifact_type), []).append(artifact)

    issues: list[ValidationIssue] = []
    family_participants: dict[tuple[str, str], set[str]] = {}
    for edge_id, edge in repository.relation_edges_by_id.items():
        if edge.get("relation_type") != "supersedes":
            continue

        from_endpoint = edge.get("from", {})
        to_endpoint = edge.get("to", {})
        if from_endpoint.get("kind") != "artifact" or to_endpoint.get("kind") != "artifact":
            continue

        source = repository.artifacts_by_id.get(from_endpoint.get("id"))
        target = repository.artifacts_by_id.get(to_endpoint.get("id"))
        if source is None or target is None:
            continue

        source_feature_key = _get_artifact_feature_key(source.header)
        target_feature_key = _get_artifact_feature_key(target.header)
        if (
            source_feature_key is None
            or target_feature_key is None
            or source.artifact_type != target.artifact_type
            or source_feature_key != target_feature_key
        ):
            issues.append(
                ValidationIssue(
                    "supersedes_family_mismatch",
                    f"{edge_id} supersedes relation must link artifacts from the same artifact_type and feature_key",
                    edge_id,
                )
            )
            continue

        family_key = (source_feature_key, source.artifact_type)
        family_participants.setdefault(family_key, set()).update(
            [source.artifact_id, target.artifact_id]
        )

        source_version = source.header.get("version")
        target_version = target.header.get("version")
        if (
            isinstance(source_version, str)
            and isinstance(target_version, str)
            and source_version == target_version
        ):
            issues.append(
                ValidationIssue(
                    "supersedes_same_version",
                    f"{edge_id} links {source.artifact_id} and {target.artifact_id} with the same version '{source_version}'",
                    edge_id,
                )
            )

    for family_key, artifacts in artifact_families.items():
        if len(artifacts) < 2:
            continue
        governed_artifacts = [
            artifact for artifact in artifacts if artifact.status not in editable_statuses
        ]
        if len(governed_artifacts) < 2:
            continue

        participants = family_participants.get(family_key, set())
        for artifact in governed_artifacts:
            if artifact.status not in immutable_statuses:
                continue
            if artifact.artifact_id in participants:
                continue
            issues.append(
                ValidationIssue(
                    "missing_supersedes_link",
                    f"{artifact.artifact_id} is in immutable status '{artifact.status}' but its artifact family has multiple versions without an artifact-level supersedes link",
                    artifact.artifact_id,
                    str(artifact.path),
                )
            )

    return issues


def _validate_required_review_records(artifact, state_machine: dict, status_rank: dict[str, int]) -> list[ValidationIssue]:
    if not _status_at_least(artifact.status, "approved", status_rank):
        return []

    state_actors = state_machine.get("state_actors", {})
    required_roles = state_actors.get("required_reviewer_roles", [])
    review_records = artifact.header.get("review_records", [])
    if not isinstance(review_records, list):
        review_records = []

    approved_roles: set[str] = set()
    for record in review_records:
        if not isinstance(record, dict):
            continue
        reviewer = record.get("reviewer", {})
        if not isinstance(reviewer, dict):
            continue
        role = reviewer.get("role")
        decision = record.get("decision")
        related_transition = record.get("related_transition")
        if decision != "approve":
            continue
        if related_transition not in (None, "in_review->approved"):
            continue
        if isinstance(role, str):
            approved_roles.add(role)

    issues: list[ValidationIssue] = []
    for role in required_roles:
        if role in approved_roles:
            continue
        issues.append(
            ValidationIssue(
                "missing_required_review_record",
                f"{artifact.artifact_id} requires an approve review_record from role '{role}' before status '{artifact.status}'",
                artifact.artifact_id,
                str(artifact.path),
            )
        )
    return issues


def _validate_git_immutable_mutations(repository: Repository, schema: dict) -> list[ValidationIssue]:
    state_model = schema.get("state_model", {})
    immutable_statuses = {
        status for status in state_model.get("immutable_statuses", []) if isinstance(status, str)
    }
    allowed_fields = {
        field
        for field in state_model.get("immutable_allowed_update_fields", [])
        if isinstance(field, str)
    }
    if not immutable_statuses:
        return []

    committed_cache: dict[Path, object] = {}
    issues: list[ValidationIssue] = []
    for artifact in repository.artifacts_by_id.values():
        if artifact.status not in immutable_statuses:
            continue

        committed = _load_head_artifact(artifact.path, committed_cache)
        if committed is None:
            continue
        if committed.artifact_id != artifact.artifact_id:
            continue
        if committed.header.get("version") != artifact.header.get("version"):
            continue
        if committed.status != artifact.status:
            continue

        current_snapshot = _immutable_protected_snapshot(artifact, allowed_fields)
        committed_snapshot = _immutable_protected_snapshot(committed, allowed_fields)
        if current_snapshot == committed_snapshot:
            continue

        issues.append(
            ValidationIssue(
                "immutable_artifact_mutation",
                f"{artifact.artifact_id} is in immutable status '{artifact.status}' and changed protected content in place without a version change",
                artifact.artifact_id,
                str(artifact.path),
            )
        )

    return issues


def _load_head_artifact(path: Path, committed_cache: dict[Path, object]) -> object | None:
    resolved_path = path.resolve()
    if resolved_path in committed_cache:
        cached = committed_cache[resolved_path]
        return None if cached is False else cached

    repo_root_result = _run_git_capture(
        resolved_path.parent,
        ["rev-parse", "--show-toplevel"],
    )
    if repo_root_result is None:
        committed_cache[resolved_path] = False
        return None
    if repo_root_result.returncode != 0:
        committed_cache[resolved_path] = False
        return None

    repo_root = Path(repo_root_result.stdout.strip())
    try:
        relative_path = resolved_path.relative_to(repo_root)
    except ValueError:
        committed_cache[resolved_path] = False
        return None

    show_result = _run_git_capture(
        repo_root,
        ["--no-pager", "show", f"HEAD:{relative_path.as_posix()}"],
    )
    if show_result is None:
        committed_cache[resolved_path] = False
        return None
    if show_result.returncode != 0:
        committed_cache[resolved_path] = False
        return None

    try:
        artifact = parse_artifact_text(show_result.stdout, path=resolved_path)
    except ValueError:
        committed_cache[resolved_path] = False
        return None

    committed_cache[resolved_path] = artifact
    return artifact


def _run_git_capture(cwd: Path, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_PAGER"] = "cat"

    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=_GIT_LOOKUP_TIMEOUT_SECONDS,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _immutable_protected_snapshot(artifact, allowed_fields: set[str]) -> dict:
    protected_header = {
        key: value
        for key, value in artifact.header.items()
        if key not in allowed_fields
    }
    return {
        "header": protected_header,
        "body": artifact.body,
        "trace_units": artifact.trace_units,
        "relation_edges": artifact.relation_edges,
    }


def _validate_status_transition_history(artifact, state_machine: dict) -> list[ValidationIssue]:
    status_history = artifact.header.get("status_history", [])
    if not isinstance(status_history, list) or not status_history:
        return []

    transitions = state_machine.get("transitions", [])
    allowed_transitions = {
        (transition.get("from"), transition.get("to"))
        for transition in transitions
        if isinstance(transition, dict)
        and isinstance(transition.get("from"), str)
        and isinstance(transition.get("to"), str)
    }

    issues: list[ValidationIssue] = []
    previous_to_status: str | None = None
    last_to_status: str | None = None

    for index, record in enumerate(status_history):
        if not isinstance(record, dict):
            continue

        from_status = record.get("from_status")
        to_status = record.get("to_status")
        if not isinstance(from_status, str) or not isinstance(to_status, str):
            continue

        if (from_status, to_status) not in allowed_transitions:
            issues.append(
                ValidationIssue(
                    "invalid_status_transition",
                    f"{artifact.artifact_id} has invalid status_history transition '{from_status} -> {to_status}' for artifact_type '{artifact.artifact_type}'",
                    artifact.artifact_id,
                    str(artifact.path),
                )
            )

        if previous_to_status is not None and from_status != previous_to_status:
            issues.append(
                ValidationIssue(
                    "status_history_sequence_mismatch",
                    f"{artifact.artifact_id} status_history sequence mismatch at index {index}: expected from_status '{previous_to_status}' but found '{from_status}'",
                    artifact.artifact_id,
                    str(artifact.path),
                )
            )

        previous_to_status = to_status
        last_to_status = to_status

    if last_to_status is not None and last_to_status != artifact.status:
        issues.append(
            ValidationIssue(
                "status_history_current_status_mismatch",
                f"{artifact.artifact_id} current status '{artifact.status}' does not match last status_history to_status '{last_to_status}'",
                artifact.artifact_id,
                str(artifact.path),
            )
        )

    return issues


def _validate_status_history(artifact, status_rank: dict[str, int]) -> list[ValidationIssue]:
    required_statuses = _required_status_history_targets(artifact.status, status_rank)
    if not required_statuses:
        return []

    status_history = artifact.header.get("status_history", [])
    if not isinstance(status_history, list):
        status_history = []
    observed_statuses = {
        record.get("to_status")
        for record in status_history
        if isinstance(record, dict) and isinstance(record.get("to_status"), str)
    }

    issues: list[ValidationIssue] = []
    for required_status in required_statuses:
        if required_status in observed_statuses:
            continue
        issues.append(
            ValidationIssue(
                "missing_status_history_transition",
                f"{artifact.artifact_id} requires a status_history entry with to_status '{required_status}' for current status '{artifact.status}'",
                artifact.artifact_id,
                str(artifact.path),
            )
        )
    return issues


def _required_status_history_targets(status: str, status_rank: dict[str, int]) -> list[str]:
    if _status_at_least(status, "done", status_rank):
        return ["approved", "active", "done"]
    if _status_at_least(status, "active", status_rank):
        return ["approved", "active"]
    if _status_at_least(status, "approved", status_rank):
        return ["approved"]
    return []


def _iter_active_traceability_gates(repository: Repository, status_rank: dict[str, int]) -> list[tuple[str, dict]]:
    active: list[tuple[str, dict]] = []
    seen: set[tuple[str, str]] = set()

    for artifact in repository.artifacts_by_id.values():
        feature_key = _get_artifact_feature_key(artifact.header)
        if feature_key is None:
            continue

        for gate in STATUS_AWARE_TRACEABILITY_GATES:
            if artifact.artifact_type != gate["artifact_type"]:
                continue
            if not _status_at_least(artifact.status, gate["minimum_status"], status_rank):
                continue
            gate_key = (feature_key, gate["artifact_type"])
            if gate_key in seen:
                continue
            seen.add(gate_key)
            active.append((feature_key, gate))

    return active


def _calculate_scope_coverage(
    repository: Repository,
    *,
    feature_key: str,
    upstream_type: str,
    downstream_type: str,
    relation_type: str,
) -> dict[str, list[str]]:
    covered: set[str] = set()
    for edge in repository.relation_edges_by_id.values():
        if edge.get("relation_type") != relation_type:
            continue

        from_id = edge.get("from", {}).get("id")
        to_id = edge.get("to", {}).get("id")
        from_record = repository.trace_units_by_id.get(from_id)
        to_record = repository.trace_units_by_id.get(to_id)
        if from_record is None or to_record is None:
            continue

        if from_record.unit.get("type") != upstream_type:
            continue
        if to_record.unit.get("type") != downstream_type:
            continue

        if _get_record_feature_key(repository, from_record) != feature_key:
            continue
        if _get_record_feature_key(repository, to_record) != feature_key:
            continue

        covered.add(from_record.unit["id"])

    upstream_ids = sorted(
        unit_id
        for unit_id, record in repository.trace_units_by_id.items()
        if record.unit.get("type") == upstream_type and _get_record_feature_key(repository, record) == feature_key
    )
    missing = sorted(unit_id for unit_id in upstream_ids if unit_id not in covered)
    return {
        "covered": sorted(covered),
        "missing": missing,
    }


def _status_at_least(status: str, minimum_status: str, status_rank: dict[str, int]) -> bool:
    return status_rank.get(status, -1) >= status_rank.get(minimum_status, -1)


def _get_record_feature_key(repository: Repository, record) -> str | None:
    artifact = repository.artifacts_by_id.get(record.artifact_id)
    if artifact is None:
        return None
    return _get_artifact_feature_key(artifact.header)


def _get_artifact_feature_key(header: dict) -> str | None:
    scope = header.get("scope")
    if not isinstance(scope, dict):
        return None
    feature_key = scope.get("feature_key")
    if isinstance(feature_key, str):
        return feature_key
    return None
