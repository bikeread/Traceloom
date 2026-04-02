from __future__ import annotations

from argparse import ArgumentParser
import json
from pathlib import Path

from traceloom.bootstrap import apply_bootstrap_seed_to_workspace, prepare_requirement_bootstrap
from traceloom.design_checks import check_design_completeness
from traceloom.defaults import resolve_default_schema_path
from traceloom.bundled_assets import resolve_bundled_demo_root
from traceloom.guided_actions import execute_guided_action_package, prepare_guided_action_package
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
from traceloom.repository import load_repository
from traceloom.validators import calculate_coverage, load_schema, trace_related_units, validate_repository
from traceloom.workspaces import create_workspace_from_starter, get_workspace, list_workspaces
from traceloom.workflows import evaluate_artifact_workflow
from traceloom.write_ops import (
    create_artifact_draft,
    promote_artifact_status,
    record_review_decision,
    record_validation_result,
    revise_artifact_draft,
    supersede_artifact_version,
)


DEFAULT_SCHEMA_PATH = resolve_default_schema_path(module_file=__file__)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="traceloom")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate artifact structure, traceability, and governance for one repository path set.",
    )
    validate_parser.add_argument("paths", nargs="+")
    validate_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))

    workspace_parser = subparsers.add_parser(
        "workspace",
        help="Advanced local workflow helpers for creating and inspecting managed workspaces.",
    )
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command", required=True)

    workspace_create_parser = workspace_subparsers.add_parser("create")
    workspace_create_parser.add_argument("name")
    workspace_create_parser.add_argument("--root")
    workspace_create_parser.add_argument("--template", choices=["minimal", "full"], default="minimal")

    workspace_list_parser = workspace_subparsers.add_parser("list")
    workspace_list_parser.add_argument("--root")

    workspace_show_parser = workspace_subparsers.add_parser("show")
    workspace_show_parser.add_argument("name")
    workspace_show_parser.add_argument("--root")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Advanced local workflow for requirement bootstrap preparation and baseline materialization.",
    )
    bootstrap_subparsers = bootstrap_parser.add_subparsers(dest="bootstrap_command", required=True)

    bootstrap_prepare_parser = bootstrap_subparsers.add_parser("prepare")
    bootstrap_prepare_parser.add_argument("--request-file", required=True)

    bootstrap_apply_parser = bootstrap_subparsers.add_parser("apply")
    bootstrap_apply_parser.add_argument("--seed-file", required=True)
    bootstrap_apply_parser.add_argument("--workspace", required=True)
    bootstrap_apply_parser.add_argument("--root")
    bootstrap_apply_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))

    trace_parser = subparsers.add_parser("trace")
    trace_parser.add_argument("trace_unit_id")
    trace_parser.add_argument("--paths", nargs="+", default=["examples"])
    trace_parser.add_argument("--direction", choices=["upstream", "downstream", "both"], default="both")

    artifact_parser = subparsers.add_parser("artifact")
    artifact_parser.add_argument("artifact_id")
    artifact_parser.add_argument("--paths", nargs="+")
    artifact_parser.add_argument("--workspace")
    artifact_parser.add_argument("--root")
    artifact_parser.add_argument("--view", choices=["header", "trace_only", "full"], default="full")

    unit_parser = subparsers.add_parser("unit")
    unit_parser.add_argument("trace_unit_id")
    unit_parser.add_argument("--paths", nargs="+", default=["examples"])

    related_parser = subparsers.add_parser("related")
    related_parser.add_argument("object_id")
    related_parser.add_argument("--paths", nargs="+", default=["examples"])
    related_parser.add_argument("--direction", choices=["upstream", "downstream", "both"], default="both")
    related_parser.add_argument("--relation-type")

    trace_upstream_parser = subparsers.add_parser("trace-upstream")
    trace_upstream_parser.add_argument("trace_unit_id")
    trace_upstream_parser.add_argument("--paths", nargs="+", default=["examples"])
    trace_upstream_parser.add_argument("--stop-at-type")

    trace_downstream_parser = subparsers.add_parser("trace-downstream")
    trace_downstream_parser.add_argument("trace_unit_id")
    trace_downstream_parser.add_argument("--paths", nargs="+", default=["examples"])
    trace_downstream_parser.add_argument("--stop-at-type")

    history_parser = subparsers.add_parser("history")
    history_parser.add_argument("artifact_id")
    history_parser.add_argument("--paths", nargs="+", default=["examples"])

    questions_parser = subparsers.add_parser("questions")
    questions_parser.add_argument("--paths", nargs="+", default=["examples"])
    questions_parser.add_argument("--artifact-id")
    questions_parser.add_argument("--status")

    versions_parser = subparsers.add_parser("versions")
    versions_parser.add_argument("artifact_id")
    versions_parser.add_argument("--paths", nargs="+", default=["examples"])

    diff_versions_parser = subparsers.add_parser("diff-versions")
    diff_versions_parser.add_argument("artifact_id")
    diff_versions_parser.add_argument("from_version")
    diff_versions_parser.add_argument("to_version")
    diff_versions_parser.add_argument("--paths", nargs="+", default=["examples"])

    coverage_parser = subparsers.add_parser("coverage")
    coverage_parser.add_argument("upstream_type")
    coverage_parser.add_argument("downstream_type")
    coverage_parser.add_argument("--paths", nargs="+", default=["examples"])
    coverage_parser.add_argument("--relation-type")

    workflow_parser = subparsers.add_parser(
        "workflow",
        help="Inspect the current workflow gate result for one artifact version.",
    )
    workflow_parser.add_argument("artifact_id")
    workflow_parser.add_argument("--paths", nargs="+", default=["examples"])
    workflow_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))

    design_check_parser = subparsers.add_parser(
        "design-check",
        help="Check whether the current solution design slice is complete enough for handoff.",
    )
    design_check_parser.add_argument("feature_key")
    design_check_parser.add_argument("--paths", nargs="+")
    design_check_parser.add_argument("--workspace")
    design_check_parser.add_argument("--root")
    design_check_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))

    navigate_feature_parser = subparsers.add_parser(
        "navigate-feature",
        help="Inspect the current feature slice stage and the next recommended action.",
    )
    navigate_feature_parser.add_argument("feature_key")
    navigate_feature_parser.add_argument("--paths", nargs="+")
    navigate_feature_parser.add_argument("--workspace")
    navigate_feature_parser.add_argument("--root")
    navigate_feature_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))

    prepare_guided_action_parser = subparsers.add_parser("prepare-guided-action")
    prepare_guided_action_parser.add_argument("feature_key")
    prepare_guided_action_parser.add_argument("--paths", nargs="+")
    prepare_guided_action_parser.add_argument("--workspace")
    prepare_guided_action_parser.add_argument("--root")
    prepare_guided_action_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    prepare_guided_action_parser.add_argument("--request-file", required=True)

    execute_guided_action_parser = subparsers.add_parser("execute-guided-action")
    execute_guided_action_parser.add_argument("--paths", nargs="+")
    execute_guided_action_parser.add_argument("--workspace")
    execute_guided_action_parser.add_argument("--root")
    execute_guided_action_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    execute_guided_action_parser.add_argument("--package-file", required=True)

    create_draft_parser = subparsers.add_parser("create-artifact-draft")
    create_draft_parser.add_argument("--paths", nargs="+", required=True)
    create_draft_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    create_draft_parser.add_argument("--path", required=True)
    create_draft_parser.add_argument("--artifact-id", required=True)
    create_draft_parser.add_argument("--artifact-type", required=True)
    create_draft_parser.add_argument("--title", required=True)
    create_draft_parser.add_argument("--summary", required=True)
    create_draft_parser.add_argument("--version", required=True)
    create_draft_parser.add_argument("--actor-id", required=True)
    create_draft_parser.add_argument("--role", required=True)
    create_draft_parser.add_argument("--capability")
    create_draft_parser.add_argument("--decision-authority")
    create_draft_parser.add_argument("--product-area", required=True)
    create_draft_parser.add_argument("--feature-key", required=True)
    create_draft_parser.add_argument("--in-scope", action="append", required=True)
    create_draft_parser.add_argument("--out-of-scope", action="append")
    create_draft_parser.add_argument("--created-at", required=True)

    revise_draft_parser = subparsers.add_parser("revise-artifact-draft")
    revise_draft_parser.add_argument("artifact_id")
    revise_draft_parser.add_argument("--paths", nargs="+", required=True)
    revise_draft_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    revise_draft_parser.add_argument("--body-file", required=True)
    revise_draft_parser.add_argument("--title")
    revise_draft_parser.add_argument("--summary")
    revise_draft_parser.add_argument("--updated-at", required=True)

    review_write_parser = subparsers.add_parser("record-review-decision")
    review_write_parser.add_argument("artifact_id")
    review_write_parser.add_argument("--paths", nargs="+", required=True)
    review_write_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    review_write_parser.add_argument("--actor-id", required=True)
    review_write_parser.add_argument("--role", required=True)
    review_write_parser.add_argument("--capability")
    review_write_parser.add_argument("--decision-authority")
    review_write_parser.add_argument("--decision", required=True)
    review_write_parser.add_argument("--recorded-at", required=True)
    review_write_parser.add_argument("--note")
    review_write_parser.add_argument("--related-transition")

    validation_write_parser = subparsers.add_parser("record-validation-result")
    validation_write_parser.add_argument("artifact_id")
    validation_write_parser.add_argument("--paths", nargs="+", required=True)
    validation_write_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    validation_write_parser.add_argument("--validator-name", required=True)
    validation_write_parser.add_argument("--result", required=True)
    validation_write_parser.add_argument("--recorded-at", required=True)
    validation_write_parser.add_argument("--note")

    promote_parser = subparsers.add_parser("promote-artifact-status")
    promote_parser.add_argument("artifact_id")
    promote_parser.add_argument("target_status")
    promote_parser.add_argument("--paths", nargs="+", required=True)
    promote_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    promote_parser.add_argument("--actor-id", required=True)
    promote_parser.add_argument("--role", required=True)
    promote_parser.add_argument("--capability")
    promote_parser.add_argument("--decision-authority")
    promote_parser.add_argument("--changed-at", required=True)

    supersede_parser = subparsers.add_parser("supersede-artifact-version")
    supersede_parser.add_argument("successor_artifact_id")
    supersede_parser.add_argument("predecessor_artifact_id")
    supersede_parser.add_argument("--paths", nargs="+", required=True)
    supersede_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    supersede_parser.add_argument("--edge-id", required=True)
    supersede_parser.add_argument("--actor-id", required=True)
    supersede_parser.add_argument("--role", required=True)
    supersede_parser.add_argument("--capability")
    supersede_parser.add_argument("--decision-authority")
    supersede_parser.add_argument("--created-at", required=True)

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Run the read-only MCP runtime over a repository or the bundled demo.",
    )
    mcp_parser.add_argument("--paths", nargs="+")
    mcp_parser.add_argument("--demo", action="store_true")
    mcp_parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_PATH))
    mcp_parser.add_argument("--print-tools", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        schema = load_schema(args.schema)
        repository = load_repository(args.paths)
        issues = validate_repository(repository, schema)
        if issues:
            for issue in issues:
                print(f"ERROR {issue.code}: {issue.message}")
            print(f"Validation failed: {len(issues)} issue(s)")
            return 1
        print("Validation passed: 0 issues")
        return 0

    if args.command == "workspace":
        if args.workspace_command == "create":
            workspace = create_workspace_from_starter(args.name, root=args.root, template=args.template)
            print(json.dumps(workspace.to_dict(), indent=2, sort_keys=True))
            return 0
        if args.workspace_command == "list":
            payload = [workspace.to_dict() for workspace in list_workspaces(root=args.root)]
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.workspace_command == "show":
            workspace = get_workspace(args.name, root=args.root)
            print(json.dumps(workspace.to_dict(), indent=2, sort_keys=True))
            return 0

    if args.command == "bootstrap":
        if args.bootstrap_command == "prepare":
            request = _load_json_file(args.request_file)
            result = prepare_requirement_bootstrap(request)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.bootstrap_command == "apply":
            seed = _load_json_file(args.seed_file)
            workspace = get_workspace(args.workspace, root=args.root)
            result = apply_bootstrap_seed_to_workspace(workspace, seed, schema_path=args.schema)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

    if args.command == "mcp":
        from traceloom.mcp_server import build_mcp_server, list_registered_tools, run_stdio_server

        if args.demo and args.paths:
            parser.error("--demo cannot be used together with --paths")

        resolved_paths = [str(resolve_bundled_demo_root())] if args.demo else (args.paths or ["examples"])

        if args.print_tools:
            build_mcp_server(paths=resolved_paths, schema_path=args.schema)
            for tool_name in list_registered_tools():
                print(tool_name)
            return 0
        run_stdio_server(paths=resolved_paths, schema_path=args.schema)
        return 0

    if args.command == "navigate-feature":
        schema = load_schema(args.schema)
        repository = load_repository(_resolve_repository_paths(args, default_paths=["examples"]))
        payload = get_delivery_slice_navigation(repository, schema, args.feature_key)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "design-check":
        schema = load_schema(args.schema)
        repository = load_repository(_resolve_repository_paths(args, default_paths=["examples"]))
        payload = check_design_completeness(repository, schema, args.feature_key)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "prepare-guided-action":
        schema = load_schema(args.schema)
        repository = load_repository(_resolve_repository_paths(args, default_paths=["examples"]))
        request = _load_json_file(args.request_file)
        result = prepare_guided_action_package(
            repository,
            schema,
            feature_key=args.feature_key,
            request=request,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "execute-guided-action":
        package = _load_json_file(args.package_file)
        result = execute_guided_action_package(
            _require_single_repo_path(_resolve_repository_paths(args, default_paths=["examples"])),
            package=package,
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "create-artifact-draft":
        result = create_artifact_draft(
            _require_single_repo_path(args.paths),
            relative_path=args.path,
            artifact_type=args.artifact_type,
            artifact_id=args.artifact_id,
            title=args.title,
            summary=args.summary,
            version=args.version,
            owner=_build_actor_ref(args),
            scope=_build_scope_payload(args),
            created_at=args.created_at,
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "revise-artifact-draft":
        result = revise_artifact_draft(
            _require_single_repo_path(args.paths),
            artifact_id=args.artifact_id,
            body=Path(args.body_file).read_text(encoding="utf-8"),
            header_updates=_build_revision_header_updates(args),
            updated_at=args.updated_at,
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "record-review-decision":
        result = record_review_decision(
            _require_single_repo_path(args.paths),
            artifact_id=args.artifact_id,
            review_record=_build_review_record(args),
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "record-validation-result":
        result = record_validation_result(
            _require_single_repo_path(args.paths),
            artifact_id=args.artifact_id,
            validation_record=_build_validation_record(args),
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "promote-artifact-status":
        result = promote_artifact_status(
            _require_single_repo_path(args.paths),
            artifact_id=args.artifact_id,
            target_status=args.target_status,
            changed_by=_build_actor_ref(args),
            changed_at=args.changed_at,
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "supersede-artifact-version":
        result = supersede_artifact_version(
            _require_single_repo_path(args.paths),
            successor_artifact_id=args.successor_artifact_id,
            predecessor_artifact_id=args.predecessor_artifact_id,
            edge_id=args.edge_id,
            created_at=args.created_at,
            created_by=_build_actor_ref(args),
            schema_path=args.schema,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    repository = load_repository(_resolve_repository_paths(args, default_paths=["examples"]))

    try:
        if args.command == "trace":
            related_ids = trace_related_units(repository, args.trace_unit_id, direction=args.direction)
            for object_id in related_ids:
                print(object_id)
            return 0

        if args.command == "artifact":
            print(json.dumps(get_artifact(repository, args.artifact_id, view=args.view), indent=2, sort_keys=True))
            return 0

        if args.command == "unit":
            print(json.dumps(get_trace_unit(repository, args.trace_unit_id), indent=2, sort_keys=True))
            return 0

        if args.command == "related":
            print(
                json.dumps(
                    list_related(
                        repository,
                        args.object_id,
                        direction=args.direction,
                        relation_type=args.relation_type,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "trace-upstream":
            print(json.dumps(trace_upstream(repository, args.trace_unit_id, stop_at_type=args.stop_at_type)))
            return 0

        if args.command == "trace-downstream":
            print(json.dumps(trace_downstream(repository, args.trace_unit_id, stop_at_type=args.stop_at_type)))
            return 0

        if args.command == "history":
            print(json.dumps(get_status_history(repository, args.artifact_id), indent=2, sort_keys=True))
            return 0

        if args.command == "questions":
            print(
                json.dumps(
                    list_open_questions(
                        repository,
                        artifact_id=args.artifact_id,
                        status=args.status,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "versions":
            print(json.dumps(list_artifact_versions(repository, args.artifact_id), indent=2, sort_keys=True))
            return 0

        if args.command == "diff-versions":
            print(
                json.dumps(
                    diff_versions(
                        repository,
                        args.artifact_id,
                        args.from_version,
                        args.to_version,
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "coverage":
            coverage = calculate_coverage(
                repository,
                args.upstream_type,
                args.downstream_type,
                relation_type=args.relation_type,
            )
            print(f"covered: {len(coverage['covered'])}")
            print(f"missing: {len(coverage['missing'])}")
            if coverage["covered"]:
                print("covered_ids: " + ", ".join(coverage["covered"]))
            if coverage["missing"]:
                print("missing_ids: " + ", ".join(coverage["missing"]))
            return 0

        if args.command == "workflow":
            schema = load_schema(args.schema)
            print(
                json.dumps(
                    evaluate_artifact_workflow(repository, schema, args.artifact_id),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
    except (KeyError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1

    parser.print_help()
    return 1


def _require_single_repo_path(paths: list[str]) -> str:
    if len(paths) != 1:
        raise ValueError("write commands require exactly one repository path")
    return paths[0]


def _load_json_file(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_review_record(args) -> dict:
    review_record = {
        "reviewer": _build_actor_ref(args),
        "decision": args.decision,
        "recorded_at": args.recorded_at,
    }
    if args.note:
        review_record["note"] = args.note
    if args.related_transition:
        review_record["related_transition"] = args.related_transition
    return review_record


def _build_validation_record(args) -> dict:
    validation_record = {
        "validator_name": args.validator_name,
        "result": args.result,
        "recorded_at": args.recorded_at,
    }
    if args.note:
        validation_record["note"] = args.note
    return validation_record


def _build_actor_ref(args) -> dict:
    actor_ref = {
        "actor_id": args.actor_id,
        "role": args.role,
    }
    if getattr(args, "capability", None):
        actor_ref["capability"] = args.capability
    if getattr(args, "decision_authority", None):
        actor_ref["decision_authority"] = args.decision_authority
    return actor_ref


def _build_scope_payload(args) -> dict:
    scope = {
        "product_area": args.product_area,
        "feature_key": args.feature_key,
        "in_scope": list(args.in_scope),
    }
    if args.out_of_scope:
        scope["out_of_scope"] = list(args.out_of_scope)
    return scope


def _build_revision_header_updates(args) -> dict:
    header_updates = {}
    if args.title is not None:
        header_updates["title"] = args.title
    if args.summary is not None:
        header_updates["summary"] = args.summary
    return header_updates


def _resolve_repository_paths(args, *, default_paths: list[str]) -> list[str]:
    paths = getattr(args, "paths", None)
    workspace_name = getattr(args, "workspace", None)

    if paths and workspace_name:
        raise ValueError("--paths cannot be used together with --workspace")
    if workspace_name:
        workspace = get_workspace(workspace_name, root=getattr(args, "root", None))
        return [str(workspace.active_repository_path)]
    if paths:
        return list(paths)
    return list(default_paths)
