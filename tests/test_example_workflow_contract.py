from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import"
VERSIONED_EXAMPLE_DIR = REPO_ROOT / "examples" / "user-tag-bulk-import-versioned"


def _load_header(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


def _approval_roles_for(path: Path) -> list[str]:
    header = _load_header(path)
    roles = [
        record.get("reviewer", {}).get("role")
        for record in header.get("review_records", [])
        if record.get("decision") == "approve"
    ]
    return sorted(role for role in roles if isinstance(role, str))


def test_example_golden_path_review_roles_match_canonical_track_b_gate_contract():
    assert _approval_roles_for(EXAMPLE_DIR / "01_brief.md") == ["pm"]
    assert _approval_roles_for(EXAMPLE_DIR / "02_prd.md") == ["qa", "tech_lead"]
    assert _approval_roles_for(EXAMPLE_DIR / "03_solution_design.md") == ["tech_lead"]
    assert _approval_roles_for(EXAMPLE_DIR / "04_execution_plan.md") == ["tech_lead"]
    assert _approval_roles_for(EXAMPLE_DIR / "05_test_acceptance.md") == ["qa"]
    assert _approval_roles_for(EXAMPLE_DIR / "06_release_review.md") == ["qa", "release_owner", "tech_lead"]


def test_versioned_example_baseline_review_roles_match_canonical_track_b_gate_contract():
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "01_brief.md") == ["pm"]
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "02_prd.md") == ["qa", "tech_lead"]
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "03_solution_design.md") == ["tech_lead"]
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "04_execution_plan.md") == ["tech_lead"]
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "05_test_acceptance.md") == ["qa"]
    assert _approval_roles_for(VERSIONED_EXAMPLE_DIR / "06_release_review.md") == ["qa", "release_owner", "tech_lead"]
