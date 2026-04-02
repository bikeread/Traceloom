from __future__ import annotations

from traceloom.artifact_io import render_yaml_block


def render_artifact_scaffold(schema: dict, artifact_type: str) -> str:
    artifact_definition = schema["artifacts"][artifact_type]
    sections = list(artifact_definition.get("required_content_sections", []))
    sections.extend(artifact_definition.get("optional_content_sections", []))

    rendered_sections: list[str] = []
    for section_name in sections:
        rendered_sections.append(f"## {_humanize_section_name(section_name)}\n\n")

    rendered_sections.append("## Trace Units\n\n")
    rendered_sections.append(render_yaml_block([]))
    rendered_sections.append("\n## Relation Edges\n\n")
    rendered_sections.append(render_yaml_block([]))
    return "".join(rendered_sections)


def _humanize_section_name(section_name: str) -> str:
    words = section_name.replace("_", " ").split()
    heading = " ".join(word.capitalize() for word in words)
    return heading.replace("Non Functional", "Non-functional")
