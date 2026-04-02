from __future__ import annotations

from pathlib import Path


DEFAULT_SCHEMA_FILENAME = "04_schema_v1.yaml"
DEFAULT_WORKSPACE_ROOT_DIRNAME = ".traceloom/workspaces"


def resolve_default_schema_path(
    *,
    cwd: str | Path | None = None,
    module_file: str | Path | None = None,
) -> Path:
    current_dir = Path.cwd() if cwd is None else Path(cwd)
    cwd_candidate = current_dir / DEFAULT_SCHEMA_FILENAME
    if cwd_candidate.is_file():
        return cwd_candidate.resolve()

    if module_file is None:
        module_path = Path(__file__).resolve()
    else:
        module_path = Path(module_file).resolve()

    packaged_candidate = module_path.parent / "resources" / DEFAULT_SCHEMA_FILENAME
    if packaged_candidate.is_file():
        return packaged_candidate.resolve()

    repo_candidate = module_path.parents[1] / DEFAULT_SCHEMA_FILENAME
    if repo_candidate.exists() and not repo_candidate.is_file():
        raise ValueError(f"default schema path candidate is not a file: {repo_candidate}")
    return repo_candidate


def resolve_workspace_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root).resolve()

    return (Path.cwd() / DEFAULT_WORKSPACE_ROOT_DIRNAME).resolve()
