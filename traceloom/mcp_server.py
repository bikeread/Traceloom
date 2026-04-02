from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from traceloom.design_checks import check_design_completeness
from traceloom.defaults import resolve_default_schema_path
from traceloom.navigation import get_delivery_slice_navigation
from traceloom.queries import (
    diff_versions,
    get_artifact,
    get_status_history,
    get_trace_unit,
    list_artifact_versions,
    list_open_questions,
    list_related,
    trace_downstream,
    trace_upstream,
)
from traceloom.repository import Repository, load_repository
from traceloom.summaries import analyze_change_impact, check_feature_readiness, check_release_readiness
from traceloom.validators import calculate_coverage, load_schema, serialize_issue, validate_repository
from traceloom.workflows import evaluate_artifact_workflow


DEFAULT_SCHEMA_PATH = resolve_default_schema_path(module_file=__file__)
DEFAULT_PATHS = ("examples",)
SERVER_NAME = "Traceloom"
SERVER_INSTRUCTIONS = (
    "Read-only access to Traceloom repositories for artifact lookup, traceability, governance summaries, "
    "version inspection, and readiness checks."
)


@dataclass(frozen=True, slots=True)
class ServerContext:
    repository: Repository
    schema: dict


def list_registered_tools() -> list[str]:
    return [
        "analyze_change_impact",
        "check_design_completeness",
        "check_feature_readiness",
        "check_release_readiness",
        "diff_versions",
        "get_artifact",
        "get_delivery_slice_navigation",
        "get_artifact_workflow",
        "get_coverage",
        "get_status_history",
        "get_trace_unit",
        "list_artifact_versions",
        "list_open_questions",
        "list_related",
        "trace_downstream",
        "trace_upstream",
        "validate_repository",
    ]


def build_mcp_server(
    *,
    paths: list[str] | None = None,
    schema_path: str | Path | None = None,
) -> FastMCP:
    context = _build_context(paths=paths, schema_path=schema_path)
    server = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS, json_response=True)

    @server.tool(name="validate_repository", description="Validate the configured Traceloom repository.")
    def validate_repository_tool() -> dict:
        return _validate_repository_tool(context)

    @server.tool(name="get_artifact", description="Fetch one artifact by artifact_id.")
    def get_artifact_tool(artifact_id: str, view: str = "full") -> dict:
        return _get_artifact_tool(context, artifact_id=artifact_id, view=view)

    @server.tool(
        name="get_delivery_slice_navigation",
        description="Return the current guided delivery-slice navigation result for one feature key.",
    )
    def get_delivery_slice_navigation_tool(feature_key: str) -> dict:
        return _get_delivery_slice_navigation_tool(context, feature_key=feature_key)

    @server.tool(
        name="get_artifact_workflow",
        description="Return the current workflow gate result for one artifact version.",
    )
    def get_artifact_workflow_tool(artifact_id: str) -> dict:
        return _get_artifact_workflow_tool(context, artifact_id=artifact_id)

    @server.tool(name="get_trace_unit", description="Fetch one trace unit and its owning artifact context.")
    def get_trace_unit_tool(trace_unit_id: str) -> dict:
        return _get_trace_unit_tool(context, trace_unit_id=trace_unit_id)

    @server.tool(name="list_related", description="List directly related objects for one artifact or trace unit id.")
    def list_related_tool(
        object_id: str,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> list[dict]:
        return _list_related_tool(
            context,
            object_id=object_id,
            direction=direction,
            relation_type=relation_type,
        )

    @server.tool(name="trace_upstream", description="Traverse upstream trace-unit dependencies.")
    def trace_upstream_tool(trace_unit_id: str, stop_at_type: str | None = None) -> list[str]:
        return _trace_upstream_tool(context, trace_unit_id=trace_unit_id, stop_at_type=stop_at_type)

    @server.tool(name="trace_downstream", description="Traverse downstream trace-unit dependencies.")
    def trace_downstream_tool(trace_unit_id: str, stop_at_type: str | None = None) -> list[str]:
        return _trace_downstream_tool(context, trace_unit_id=trace_unit_id, stop_at_type=stop_at_type)

    @server.tool(name="get_status_history", description="Return artifact status history entries.")
    def get_status_history_tool(artifact_id: str) -> list[dict]:
        return _get_status_history_tool(context, artifact_id=artifact_id)

    @server.tool(name="list_open_questions", description="List open or filtered questions across the repository.")
    def list_open_questions_tool(
        artifact_id: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        return _list_open_questions_tool(context, artifact_id=artifact_id, status=status)

    @server.tool(name="list_artifact_versions", description="List all versions in one artifact family.")
    def list_artifact_versions_tool(artifact_id: str) -> list[dict]:
        return _list_artifact_versions_tool(context, artifact_id=artifact_id)

    @server.tool(name="diff_versions", description="Summarize header, trace-unit, and edge changes across versions.")
    def diff_versions_tool(artifact_id: str, from_version: str, to_version: str) -> dict:
        return _diff_versions_tool(
            context,
            artifact_id=artifact_id,
            from_version=from_version,
            to_version=to_version,
        )

    @server.tool(name="get_coverage", description="Calculate repository coverage for one upstream/downstream type pair.")
    def get_coverage_tool(
        upstream_type: str,
        downstream_type: str,
        relation_type: str | None = None,
    ) -> dict:
        return _get_coverage_tool(
            context,
            upstream_type=upstream_type,
            downstream_type=downstream_type,
            relation_type=relation_type,
        )

    @server.tool(name="check_feature_readiness", description="Summarize readiness blockers for one feature key.")
    def check_feature_readiness_tool(feature_key: str) -> dict:
        return _check_feature_readiness_tool(context, feature_key=feature_key)

    @server.tool(name="check_design_completeness", description="Check whether the current design slice is complete enough for handoff.")
    def check_design_completeness_tool(feature_key: str) -> dict:
        return _check_design_completeness_tool(context, feature_key=feature_key)

    @server.tool(name="check_release_readiness", description="Summarize readiness blockers for one release target.")
    def check_release_readiness_tool(
        release_target: str | None = None,
        feature_key: str | None = None,
    ) -> dict:
        return _check_release_readiness_tool(
            context,
            release_target=release_target,
            feature_key=feature_key,
        )

    @server.tool(name="analyze_change_impact", description="Summarize upstream, downstream, and artifact impact.")
    def analyze_change_impact_tool(object_id: str) -> dict:
        return _analyze_change_impact_tool(context, object_id=object_id)

    return server


def dispatch_tool_call(
    tool_name: str,
    arguments: dict | None = None,
    *,
    paths: list[str] | None = None,
    schema_path: str | Path | None = None,
):
    context = _build_context(paths=paths, schema_path=schema_path)
    handlers = {
        "validate_repository": lambda payload: _validate_repository_tool(context),
        "get_artifact": lambda payload: _get_artifact_tool(context, **payload),
        "get_delivery_slice_navigation": lambda payload: _get_delivery_slice_navigation_tool(context, **payload),
        "get_artifact_workflow": lambda payload: _get_artifact_workflow_tool(context, **payload),
        "get_trace_unit": lambda payload: _get_trace_unit_tool(context, **payload),
        "list_related": lambda payload: _list_related_tool(context, **payload),
        "trace_upstream": lambda payload: _trace_upstream_tool(context, **payload),
        "trace_downstream": lambda payload: _trace_downstream_tool(context, **payload),
        "get_status_history": lambda payload: _get_status_history_tool(context, **payload),
        "list_open_questions": lambda payload: _list_open_questions_tool(context, **payload),
        "list_artifact_versions": lambda payload: _list_artifact_versions_tool(context, **payload),
        "diff_versions": lambda payload: _diff_versions_tool(context, **payload),
        "get_coverage": lambda payload: _get_coverage_tool(context, **payload),
        "check_design_completeness": lambda payload: _check_design_completeness_tool(context, **payload),
        "check_feature_readiness": lambda payload: _check_feature_readiness_tool(context, **payload),
        "check_release_readiness": lambda payload: _check_release_readiness_tool(context, **payload),
        "analyze_change_impact": lambda payload: _analyze_change_impact_tool(context, **payload),
    }
    if tool_name not in handlers:
        raise KeyError(f"unsupported MCP tool '{tool_name}'")
    return handlers[tool_name](arguments or {})


def run_stdio_server(
    *,
    paths: list[str] | None = None,
    schema_path: str | Path | None = None,
) -> None:
    server = build_mcp_server(paths=paths, schema_path=schema_path)
    server.run(transport="stdio")


def _build_context(
    *,
    paths: list[str] | None,
    schema_path: str | Path | None,
) -> ServerContext:
    resolved_paths = list(paths or DEFAULT_PATHS)
    resolved_schema_path = Path(schema_path or DEFAULT_SCHEMA_PATH)
    repository = load_repository(resolved_paths)
    schema = load_schema(resolved_schema_path)
    return ServerContext(repository=repository, schema=schema)


def _validate_repository_tool(context: ServerContext) -> dict:
    issues = validate_repository(context.repository, context.schema)
    return {
        "issue_count": len(issues),
        "issues": [serialize_issue(issue) for issue in issues],
    }


def _get_artifact_tool(context: ServerContext, *, artifact_id: str, view: str = "full") -> dict:
    return get_artifact(context.repository, artifact_id, view=view)


def _get_delivery_slice_navigation_tool(context: ServerContext, *, feature_key: str) -> dict:
    return get_delivery_slice_navigation(context.repository, context.schema, feature_key)


def _get_artifact_workflow_tool(context: ServerContext, *, artifact_id: str) -> dict:
    return evaluate_artifact_workflow(context.repository, context.schema, artifact_id)


def _get_trace_unit_tool(context: ServerContext, *, trace_unit_id: str) -> dict:
    return get_trace_unit(context.repository, trace_unit_id)


def _list_related_tool(
    context: ServerContext,
    *,
    object_id: str,
    direction: str = "both",
    relation_type: str | None = None,
) -> list[dict]:
    return list_related(context.repository, object_id, direction=direction, relation_type=relation_type)


def _trace_upstream_tool(
    context: ServerContext,
    *,
    trace_unit_id: str,
    stop_at_type: str | None = None,
) -> list[str]:
    return trace_upstream(context.repository, trace_unit_id, stop_at_type=stop_at_type)


def _trace_downstream_tool(
    context: ServerContext,
    *,
    trace_unit_id: str,
    stop_at_type: str | None = None,
) -> list[str]:
    return trace_downstream(context.repository, trace_unit_id, stop_at_type=stop_at_type)


def _get_status_history_tool(context: ServerContext, *, artifact_id: str) -> list[dict]:
    return get_status_history(context.repository, artifact_id)


def _list_open_questions_tool(
    context: ServerContext,
    *,
    artifact_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    return list_open_questions(context.repository, artifact_id=artifact_id, status=status)


def _list_artifact_versions_tool(context: ServerContext, *, artifact_id: str) -> list[dict]:
    return list_artifact_versions(context.repository, artifact_id)


def _diff_versions_tool(
    context: ServerContext,
    *,
    artifact_id: str,
    from_version: str,
    to_version: str,
) -> dict:
    return diff_versions(context.repository, artifact_id, from_version, to_version)


def _get_coverage_tool(
    context: ServerContext,
    *,
    upstream_type: str,
    downstream_type: str,
    relation_type: str | None = None,
) -> dict:
    coverage = calculate_coverage(
        context.repository,
        upstream_type,
        downstream_type,
        relation_type=relation_type,
    )
    return {
        "upstream_type": upstream_type,
        "downstream_type": downstream_type,
        "relation_type": relation_type,
        "covered_ids": coverage["covered"],
        "missing_ids": coverage["missing"],
    }


def _check_feature_readiness_tool(context: ServerContext, *, feature_key: str) -> dict:
    return check_feature_readiness(context.repository, context.schema, feature_key)


def _check_design_completeness_tool(context: ServerContext, *, feature_key: str) -> dict:
    return check_design_completeness(context.repository, context.schema, feature_key)


def _check_release_readiness_tool(
    context: ServerContext,
    *,
    release_target: str | None = None,
    feature_key: str | None = None,
) -> dict:
    return check_release_readiness(
        context.repository,
        context.schema,
        release_target=release_target,
        feature_key=feature_key,
    )


def _analyze_change_impact_tool(context: ServerContext, *, object_id: str) -> dict:
    return analyze_change_impact(context.repository, object_id)
