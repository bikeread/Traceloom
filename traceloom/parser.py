from __future__ import annotations

from pathlib import Path
import re

import yaml

from traceloom.models import Artifact


FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
FENCED_YAML_PATTERN = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
HEADING_PATTERN = re.compile(r"^#{2,6}\s+(.+?)\s*$", re.MULTILINE)


def parse_artifact(path: str | Path) -> Artifact:
    artifact_path = Path(path)
    text = artifact_path.read_text(encoding="utf-8")
    return parse_artifact_text(text, path=artifact_path)


def parse_artifact_text(text: str, *, path: str | Path) -> Artifact:
    artifact_path = Path(path)
    header, body = _parse_frontmatter(text)
    trace_units, relation_edges = _parse_machine_blocks(body)
    headings = _extract_headings(body)
    return Artifact(
        path=artifact_path,
        header=header,
        body=body,
        headings=headings,
        trace_units=trace_units,
        relation_edges=relation_edges,
    )


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise ValueError("artifact frontmatter is missing")
    header = yaml.safe_load(match.group(1)) or {}
    if "artifact_id" not in header or "artifact_type" not in header:
        raise ValueError("artifact frontmatter must contain artifact_id and artifact_type")
    body = text[match.end() :].lstrip("\n")
    return header, body


def _parse_machine_blocks(body: str) -> tuple[list[dict], list[dict]]:
    trace_units: list[dict] = []
    relation_edges: list[dict] = []
    for block in FENCED_YAML_PATTERN.findall(body):
        data = yaml.safe_load(block)
        if not isinstance(data, list):
            continue
        if all(isinstance(item, dict) and {"id", "type"} <= item.keys() for item in data):
            trace_units.extend(data)
        elif all(
            isinstance(item, dict) and {"edge_id", "relation_type"} <= item.keys()
            for item in data
        ):
            relation_edges.extend(data)
    return trace_units, relation_edges


def _extract_headings(body: str) -> list[str]:
    return [match.strip() for match in HEADING_PATTERN.findall(body)]
