from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from traceloom.artifact_io import write_artifact_header
from traceloom.bundled_assets import materialize_bundled_demo_repo
from traceloom.parser import parse_artifact


def run_command(*args: str) -> str:
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def make_brief_handoff_ready(repo_root: Path) -> None:
    for relative_path in (
        "02_prd.md",
        "03_solution_design.md",
        "04_execution_plan.md",
        "05_test_acceptance.md",
        "06_release_review.md",
    ):
        target = repo_root / relative_path
        if target.exists():
            target.unlink()

    brief_path = repo_root / "01_brief.md"
    artifact = parse_artifact(brief_path)
    header = dict(artifact.header)
    header["status"] = "in_review"
    header["updated_at"] = "2026-03-26T12:00:00+08:00"
    header["status_history"] = []
    header["downstream_refs"] = []
    write_artifact_header(brief_path, header)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: python scripts/smoke_companion_bundle.py <binary-path>")

    binary_path = str(Path(argv[0]).resolve())

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        demo_root = materialize_bundled_demo_repo(temp_root / "demo")

        run_command(binary_path, "--help")
        tool_list = run_command(binary_path, "mcp", "--demo", "--print-tools")
        if "get_delivery_slice_navigation" not in tool_list:
            raise RuntimeError("expected get_delivery_slice_navigation in tool list")

        navigation_output = run_command(
            binary_path,
            "navigate-feature",
            "user-tag-bulk-import",
            "--paths",
            str(demo_root),
        )
        navigation_payload = json.loads(navigation_output)
        if navigation_payload["feature_key"] != "user-tag-bulk-import":
            raise RuntimeError("unexpected feature key from navigate-feature")

        make_brief_handoff_ready(demo_root)

        request_file = temp_root / "guided-action-request.json"
        request_file.write_text(
            json.dumps(
                {
                    "action_type": "promote_artifact_status",
                    "target_status": "approved",
                    "governance_payload": {
                        "actor_id": "user:li.pm",
                        "role": "pm",
                        "capability": "artifact_governance",
                        "decision_authority": "brief_owner",
                        "changed_at": "2026-03-26T12:10:00+08:00",
                    },
                }
            ),
            encoding="utf-8",
        )

        prepared_package = run_command(
            binary_path,
            "prepare-guided-action",
            "user-tag-bulk-import",
            "--paths",
            str(demo_root),
            "--request-file",
            str(request_file),
        )
        package_file = temp_root / "guided-action-package.json"
        package_file.write_text(prepared_package, encoding="utf-8")

        execution_output = run_command(
            binary_path,
            "execute-guided-action",
            "--paths",
            str(demo_root),
            "--package-file",
            str(package_file),
        )
        execution_payload = json.loads(execution_output)
        if not execution_payload["accepted"]:
            raise RuntimeError(f"expected accepted guided action, got: {execution_payload}")

        artifact_output = run_command(
            binary_path,
            "artifact",
            "BRIEF-2026-001",
            "--paths",
            str(demo_root),
            "--view",
            "header",
        )
        artifact_payload = json.loads(artifact_output)
        if artifact_payload["header"]["status"] != "approved":
            raise RuntimeError("guided action smoke did not promote brief to approved")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
