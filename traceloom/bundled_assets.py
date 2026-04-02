from __future__ import annotations

from importlib import resources
from pathlib import Path
import shutil


def resolve_bundled_demo_root(*, module_file: str | Path | None = None) -> Path:
    if module_file is not None:
        candidate = Path(module_file).resolve().parent / "bundled" / "demo-repo"
        if candidate.exists():
            return candidate

    return Path(str(resources.files("traceloom").joinpath("bundled", "demo-repo")))


def materialize_bundled_demo_repo(
    target_dir: str | Path,
    *,
    module_file: str | Path | None = None,
) -> Path:
    source_dir = resolve_bundled_demo_root(module_file=module_file)
    destination = Path(target_dir)

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source_dir, destination)
    return destination
