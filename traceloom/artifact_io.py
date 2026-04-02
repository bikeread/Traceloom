from __future__ import annotations

from pathlib import Path
import re

import yaml


FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def read_artifact_parts(path: str | Path) -> tuple[dict, str]:
    artifact_path = Path(path)
    text = artifact_path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    if match is None:
        raise ValueError("artifact frontmatter is missing")
    header = yaml.safe_load(match.group(1)) or {}
    body = text[match.end() :].lstrip("\n")
    return header, body


def render_artifact_text(header: dict, body: str) -> str:
    rendered_header = yaml.safe_dump(
        header,
        sort_keys=False,
        allow_unicode=False,
        default_flow_style=False,
    ).strip()
    if body:
        return f"---\n{rendered_header}\n---\n\n{body}"
    return f"---\n{rendered_header}\n---\n"


def render_yaml_block(items: list[dict]) -> str:
    rendered_yaml = yaml.safe_dump(
        items,
        sort_keys=False,
        allow_unicode=False,
        default_flow_style=False,
    ).strip()
    return f"```yaml\n{rendered_yaml}\n```\n"


def write_artifact_document(path: str | Path, header: dict, body: str) -> None:
    artifact_path = Path(path)
    artifact_path.write_text(render_artifact_text(header, body), encoding="utf-8")


def write_artifact_header(path: str | Path, header: dict) -> None:
    artifact_path = Path(path)
    _, body = read_artifact_parts(artifact_path)
    write_artifact_document(artifact_path, header, body)


def replace_trace_units_block(body: str, trace_units: list[dict]) -> str:
    return _replace_named_machine_block(body, "Trace Units", render_yaml_block(trace_units))


def replace_relation_edges_block(body: str, relation_edges: list[dict]) -> str:
    return _replace_named_machine_block(body, "Relation Edges", render_yaml_block(relation_edges))


def _replace_named_machine_block(body: str, heading: str, rendered_block: str) -> str:
    pattern = re.compile(
        rf"(?P<prefix>## {re.escape(heading)}\n\n)```yaml\n.*?\n```",
        re.DOTALL,
    )
    match = pattern.search(body)
    if match is not None:
        return body[: match.start()] + match.group("prefix") + rendered_block + body[match.end() :]

    normalized_body = body if not body or body.endswith("\n") else f"{body}\n"
    separator = "" if not normalized_body else "\n"
    return f"{normalized_body}{separator}## {heading}\n\n{rendered_block}"
