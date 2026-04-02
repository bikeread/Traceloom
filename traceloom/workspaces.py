from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil

from traceloom.defaults import resolve_workspace_root


WORKSPACE_METADATA_FILENAME = ".traceloom-workspace.json"
DEFAULT_TEMPLATE_KIND = "minimal"
MINIMAL_TEMPLATE_KIND = "minimal"
FULL_TEMPLATE_KIND = "full"
MINIMAL_WORKSPACE_SOURCE_KIND = "minimal_requirement_template"
FULL_WORKSPACE_SOURCE_KIND = "starter_template"
STARTER_TEMPLATE_DIRNAME = "starter-repo"
MINIMAL_TEMPLATE_DIRNAME = "minimal-requirement-repo"
INVALID_WORKSPACE_NAME_MESSAGE = "invalid workspace name"
INVALID_WORKSPACE_METADATA_MESSAGE = "invalid workspace metadata"
INVALID_TEMPLATE_MESSAGE = "invalid workspace template"


@dataclass(frozen=True, slots=True)
class Workspace:
    name: str
    root_path: Path
    active_repository_path: Path
    source_kind: str
    metadata_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "root_path": str(self.root_path),
            "active_repository_path": str(self.active_repository_path),
            "source_kind": self.source_kind,
        }


def create_workspace_from_starter(
    name: str,
    *,
    root: str | Path | None = None,
    template: str = DEFAULT_TEMPLATE_KIND,
) -> Workspace:
    normalized_name = normalize_workspace_name(name)
    root_path = resolve_workspace_root(root)
    workspace_path = root_path / normalized_name
    if workspace_path.exists():
        raise ValueError(f"workspace '{normalized_name}' already exists")

    template_root, source_kind = _resolve_workspace_template(template)
    workspace_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_root, workspace_path)

    workspace = Workspace(
        name=normalized_name,
        root_path=root_path,
        active_repository_path=workspace_path,
        source_kind=source_kind,
        metadata_path=_workspace_metadata_path(workspace_path),
    )
    _write_workspace_metadata(workspace)
    return workspace


def list_workspaces(*, root: str | Path | None = None) -> list[Workspace]:
    root_path = resolve_workspace_root(root)
    if not root_path.exists():
        return []

    workspaces: list[Workspace] = []
    for workspace_path in sorted(path for path in root_path.iterdir() if path.is_dir()):
        metadata_path = _workspace_metadata_path(workspace_path)
        if not metadata_path.is_file():
            continue
        try:
            workspaces.append(_read_workspace_metadata(metadata_path))
        except ValueError:
            continue
    return sorted(workspaces, key=lambda workspace: workspace.name)


def get_workspace(name: str, *, root: str | Path | None = None) -> Workspace:
    normalized_name = normalize_workspace_name(name)
    root_path = resolve_workspace_root(root)
    metadata_path = _workspace_metadata_path(root_path / normalized_name)
    if not metadata_path.is_file():
        raise KeyError(f"unknown workspace '{normalized_name}'")
    return _read_workspace_metadata(metadata_path)


def show_workspace(name: str, *, root: str | Path | None = None) -> Workspace:
    return get_workspace(name, root=root)


def _resolve_workspace_template(template: str) -> tuple[Path, str]:
    normalized_template = template.strip().lower()
    template_root: Path
    source_kind: str
    if normalized_template == MINIMAL_TEMPLATE_KIND:
        template_root = _resolve_template_root(MINIMAL_TEMPLATE_DIRNAME)
        source_kind = MINIMAL_WORKSPACE_SOURCE_KIND
    elif normalized_template == FULL_TEMPLATE_KIND:
        template_root = _resolve_template_root(STARTER_TEMPLATE_DIRNAME)
        source_kind = FULL_WORKSPACE_SOURCE_KIND
    else:
        raise ValueError(f"{INVALID_TEMPLATE_MESSAGE}: '{template}'")
    return template_root, source_kind


def _resolve_template_root(template_dirname: str) -> Path:
    module_root = Path(__file__).resolve().parents[1]
    template_root = module_root / "templates" / template_dirname
    if not template_root.is_dir():
        raise FileNotFoundError(f"workspace template directory not found: {template_root}")
    return template_root


def _workspace_metadata_path(workspace_path: Path) -> Path:
    return workspace_path / WORKSPACE_METADATA_FILENAME


def _write_workspace_metadata(workspace: Workspace) -> None:
    payload = workspace.to_dict()
    workspace.metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_workspace_metadata(metadata_path: Path) -> Workspace:
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{INVALID_WORKSPACE_METADATA_MESSAGE}: {metadata_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{INVALID_WORKSPACE_METADATA_MESSAGE}: {metadata_path}")

    required_keys = {"name", "root_path", "active_repository_path", "source_kind"}
    missing_keys = sorted(required_keys.difference(payload))
    if missing_keys:
        raise ValueError(
            f"{INVALID_WORKSPACE_METADATA_MESSAGE}: {metadata_path} missing {', '.join(missing_keys)}"
        )

    workspace_path = metadata_path.parent
    return Workspace(
        name=payload["name"],
        root_path=Path(payload["root_path"]),
        active_repository_path=Path(payload["active_repository_path"]),
        source_kind=payload["source_kind"],
        metadata_path=workspace_path / WORKSPACE_METADATA_FILENAME,
    )


def normalize_workspace_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: expected a string")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: name must not be empty")
    if normalized_name in {".", ".."}:
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: '{name}' is not allowed")
    if normalized_name.startswith(".") and normalized_name not in {".", ".."}:
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: '{name}' is not allowed")
    if any(separator and separator in normalized_name for separator in {os.sep, os.altsep, "\\", "/"}):
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: '{name}' contains path separators")
    if Path(normalized_name).is_absolute():
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: '{name}' must be relative")
    if len(Path(normalized_name).parts) != 1:
        raise ValueError(f"{INVALID_WORKSPACE_NAME_MESSAGE}: '{name}' is not a single workspace name")

    return normalized_name
