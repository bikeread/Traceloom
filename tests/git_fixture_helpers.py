from pathlib import Path
import shutil
import subprocess
import tempfile


def init_git_example_repo(example_dir: Path) -> tuple[tempfile.TemporaryDirectory, Path]:
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    fixture_root = root / "repo"
    shutil.copytree(example_dir, fixture_root)
    subprocess.run(["git", "init"], cwd=fixture_root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.name", "Traceloom Tests"],
        cwd=fixture_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "tests@example.com"],
        cwd=fixture_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "add", "."], cwd=fixture_root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=fixture_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return temp_dir, fixture_root


def replace_in_file(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace(old, new), encoding="utf-8")
