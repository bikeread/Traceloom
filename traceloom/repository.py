from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from traceloom.models import Artifact
from traceloom.parser import parse_artifact


@dataclass(slots=True)
class TraceUnitRecord:
    artifact_id: str
    artifact_type: str
    unit: dict


@dataclass(slots=True)
class Repository:
    artifacts_by_id: dict[str, Artifact]
    trace_units_by_id: dict[str, TraceUnitRecord]
    relation_edges_by_id: dict[str, dict]
    duplicate_artifact_ids: list[str] = field(default_factory=list)
    duplicate_trace_unit_ids: list[str] = field(default_factory=list)
    duplicate_relation_edge_ids: list[str] = field(default_factory=list)


def load_repository(paths: list[str | Path]) -> Repository:
    artifacts_by_id: dict[str, Artifact] = {}
    trace_units_by_id: dict[str, TraceUnitRecord] = {}
    relation_edges_by_id: dict[str, dict] = {}
    duplicate_artifact_ids: list[str] = []
    duplicate_trace_unit_ids: list[str] = []
    duplicate_relation_edge_ids: list[str] = []

    for file_path in _discover_markdown_files(paths):
        try:
            artifact = parse_artifact(file_path)
        except ValueError as exc:
            if "frontmatter is missing" in str(exc):
                continue
            raise

        if artifact.artifact_id in artifacts_by_id:
            duplicate_artifact_ids.append(artifact.artifact_id)
            continue
        artifacts_by_id[artifact.artifact_id] = artifact

        for unit in artifact.trace_units:
            unit_id = unit["id"]
            if unit_id in trace_units_by_id:
                duplicate_trace_unit_ids.append(unit_id)
                continue
            trace_units_by_id[unit_id] = TraceUnitRecord(
                artifact_id=artifact.artifact_id,
                artifact_type=artifact.artifact_type,
                unit=unit,
            )

        for edge in artifact.relation_edges:
            edge_id = edge["edge_id"]
            if edge_id in relation_edges_by_id:
                duplicate_relation_edge_ids.append(edge_id)
                continue
            relation_edges_by_id[edge_id] = edge

    return Repository(
        artifacts_by_id=artifacts_by_id,
        trace_units_by_id=trace_units_by_id,
        relation_edges_by_id=relation_edges_by_id,
        duplicate_artifact_ids=duplicate_artifact_ids,
        duplicate_trace_unit_ids=duplicate_trace_unit_ids,
        duplicate_relation_edge_ids=duplicate_relation_edge_ids,
    )


def _discover_markdown_files(paths: list[str | Path]) -> list[Path]:
    discovered: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_file() and path.suffix == ".md":
            discovered.append(path)
            continue
        if path.is_dir():
            discovered.extend(sorted(path.rglob("*.md")))
    return sorted(discovered)
