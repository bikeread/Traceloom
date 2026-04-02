from __future__ import annotations

from pathlib import Path
import shutil


REPO_ROOT = Path(__file__).resolve().parents[1]


def sync_tree(source_dir: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)


def main() -> int:
    sync_tree(
        REPO_ROOT / "examples" / "user-tag-bulk-import",
        REPO_ROOT / "traceloom" / "bundled" / "demo-repo",
    )

    schema_target = REPO_ROOT / "traceloom" / "resources" / "04_schema_v1.yaml"
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "04_schema_v1.yaml", schema_target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
