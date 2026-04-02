from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from traceloom.artifact_io import read_artifact_parts, render_yaml_block, write_artifact_document
from traceloom.defaults import resolve_default_schema_path
from traceloom.repository import load_repository
from traceloom.validators import load_schema, validate_repository

PROGRESSION_LEVELS = {
    "brief_only",
    "brief_plus_prd_seed",
    "prd_handoff_ready_seed",
}
DEFAULT_SCHEMA_PATH = resolve_default_schema_path(module_file=__file__)
STARTER_BRIEF_FILENAME = "01_brief.md"
STARTER_PRD_FILENAME = "02_prd.md"
STARTER_TEMPLATE_DIRNAME = "starter-repo"
CONNECTED_TEMPLATE_FILENAMES = (
    "02_prd.md",
    "03_solution_design.md",
    "04_execution_plan.md",
    "05_test_acceptance.md",
    "06_release_review.md",
)
REQUIRED_SECTION_TITLES = {
    "brief": (
        "Background",
        "Problem Statement",
        "Target Users",
        "Goals",
        "Success Metrics",
        "Non-goals",
    ),
    "prd_story_pack": (
        "User Scenarios",
        "Scope In",
        "Scope Out",
        "Functional Requirements",
        "Edge Cases",
        "Acceptance Criteria",
    ),
}

_GENERIC_SOURCE_TERMS = (
    "background",
    "overview",
    "general",
    "generic",
    "about the company",
    "company overview",
    "high-level background",
    "boilerplate",
    "unrelated",
    "miscellaneous",
)

_REQUIREMENT_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "that",
    "this",
    "need",
    "needs",
    "project",
}

_SOURCE_RELEVANCE_ANCHORS = (
    "requirement",
    "slice",
    "prd",
    "design",
    "handoff",
    "current",
    "onboarding",
    "constraint",
    "ticket",
    "issue",
)


def prepare_requirement_bootstrap(request: dict) -> dict:
    _validate_request_shape(request)

    intent = request["intent"]
    requirement_statement = _normalize_text(intent["current_requirement_statement"])
    conversation_text = _normalize_conversation(request["conversation"])
    primary_source = request.get("primary_source")
    supporting_sources = list(request.get("supporting_sources", []))

    admissible_sources = []
    if primary_source is not None:
        _validate_source_admissibility(
            primary_source,
            requirement_statement,
            source_label="primary_source",
            source_index=0,
        )
        admissible_sources.append(("primary_source", 0, primary_source))
    for index, source in enumerate(supporting_sources, start=1):
        _validate_source_admissibility(
            source,
            requirement_statement,
            source_label="supporting_source",
            source_index=index,
        )
        admissible_sources.append(("supporting_source", index, source))

    progression_level = _classify_progression_level(
        requirement_statement=requirement_statement,
        conversation_text=conversation_text,
        admissible_sources=admissible_sources,
    )
    if progression_level not in PROGRESSION_LEVELS:
        raise ValueError(f"unsupported progression level: {progression_level}")

    evidence_map = {
        "evidence_backed_facts": _build_evidence_backed_facts(
            requirement_statement=requirement_statement,
            conversation_text=conversation_text,
            admissible_sources=admissible_sources,
        ),
        "derived_inferences": _build_derived_inferences(
            progression_level=progression_level,
            requirement_statement=requirement_statement,
            admissible_sources=admissible_sources,
        ),
        "missing_evidence": _build_missing_evidence(progression_level),
    }

    result = {
        "progression_level": progression_level,
        "brief_draft": _build_brief_draft(
            requirement_statement=requirement_statement,
            progression_level=progression_level,
            admissible_sources=admissible_sources,
        ),
        "evidence_map": evidence_map,
        "scope_assumptions": _build_scope_assumptions(
            progression_level=progression_level,
            primary_source=primary_source,
            supporting_sources=supporting_sources,
        ),
        "open_questions": _build_open_questions(progression_level),
        "follow_up_questions": _build_follow_up_questions(progression_level),
        "eligible_next_artifact_types": _eligible_next_artifact_types(progression_level),
        "next_handoff_recommendation": _build_next_handoff_recommendation(progression_level),
    }

    if progression_level in {"brief_plus_prd_seed", "prd_handoff_ready_seed"}:
        result["prd_seed_draft"] = _build_prd_seed_draft(
            requirement_statement=requirement_statement,
            progression_level=progression_level,
            conversation_text=conversation_text,
            admissible_sources=admissible_sources,
        )

    return result


def apply_bootstrap_seed_to_workspace(
    workspace,
    seed: dict,
    *,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
) -> dict:
    workspace_name = getattr(workspace, "name", None)
    repo_root = Path(getattr(workspace, "active_repository_path", workspace))
    if not isinstance(seed, dict):
        raise ValueError("bootstrap seed must be a dict")

    normalized_seed = _normalize_materialization_seed(seed, workspace_name=workspace_name or repo_root.name)
    if normalized_seed["prd"] is not None:
        normalized_seed["prd"]["upstream_brief_artifact_id"] = normalized_seed["brief"]["artifact_id"]
    brief_path = repo_root / STARTER_BRIEF_FILENAME
    prd_path = repo_root / STARTER_PRD_FILENAME

    brief_header, _ = read_artifact_parts(brief_path)

    materialized_brief_header = _build_materialized_header(
        brief_header,
        normalized_seed["brief"],
        artifact_type="brief",
    )
    materialized_brief_body = _build_materialized_body(
        normalized_seed["brief"],
        seed=seed,
        artifact_type="brief",
        include_bootstrap_context=True,
    )

    materialized_prd_header = None
    materialized_prd_body = None
    if normalized_seed["prd"] is not None:
        prd_header = _load_optional_template_artifact_header(prd_path, STARTER_PRD_FILENAME)
        materialized_prd_header = _build_materialized_header(
            prd_header,
            normalized_seed["prd"],
            artifact_type="prd_story_pack",
        )
        _rewrite_handoff_refs(
            materialized_brief_header,
            materialized_prd_header,
            brief_artifact_id=normalized_seed["brief"]["artifact_id"],
            prd_artifact_id=normalized_seed["prd"]["artifact_id"],
        )
        materialized_prd_body = _build_materialized_body(
            normalized_seed["prd"],
            seed=seed,
            artifact_type="prd_story_pack",
            include_bootstrap_context=False,
        )

    _validate_materialized_workspace(
        repo_root,
        brief_header=materialized_brief_header,
        brief_body=materialized_brief_body,
        prd_header=materialized_prd_header,
        prd_body=materialized_prd_body,
        schema_path=schema_path,
    )

    write_artifact_document(brief_path, materialized_brief_header, materialized_brief_body)
    if materialized_prd_header is not None and materialized_prd_body is not None:
        write_artifact_document(prd_path, materialized_prd_header, materialized_prd_body)

    created_baseline = {
        "brief": {
            "artifact_id": normalized_seed["brief"]["artifact_id"],
            "path": str(brief_path),
        }
    }
    if normalized_seed["prd"] is not None:
        created_baseline["prd"] = {
            "artifact_id": normalized_seed["prd"]["artifact_id"],
            "path": str(prd_path),
        }

    return {
        "workspace_name": workspace_name or repo_root.name,
        "workspace_path": str(repo_root),
        "created_baseline": created_baseline,
    }


def _validate_request_shape(request: dict) -> None:
    if not isinstance(request, dict):
        raise ValueError("bootstrap request must be a dict")

    if "intent" not in request:
        raise ValueError("bootstrap request requires an intent dict with current_requirement_statement")
    if "conversation" not in request:
        raise ValueError("bootstrap request requires conversation content")

    intent = request["intent"]
    if not isinstance(intent, dict):
        raise ValueError("bootstrap request intent must be a dict with current_requirement_statement")

    requirement_statement = intent.get("current_requirement_statement")
    if not isinstance(requirement_statement, str) or not requirement_statement.strip():
        raise ValueError("bootstrap request intent must include current_requirement_statement")

    conversation = request["conversation"]
    if isinstance(conversation, str):
        if not conversation.strip():
            raise ValueError("bootstrap request conversation must not be empty")
    elif isinstance(conversation, list):
        if not conversation:
            raise ValueError("bootstrap request conversation must not be empty")
    else:
        raise ValueError("bootstrap request conversation must be text or message list")

    if "primary_source" in request and request["primary_source"] is not None and not isinstance(request["primary_source"], dict):
        raise ValueError("primary_source must be a dict when provided")

    supporting_sources = request.get("supporting_sources", [])
    if supporting_sources is None:
        supporting_sources = []
    if not isinstance(supporting_sources, list):
        raise ValueError("supporting_sources must be a list")
    if len(supporting_sources) > 5:
        raise ValueError("bootstrap request accepts up to five supporting sources")


def _validate_source_admissibility(
    source: dict,
    requirement_statement: str,
    *,
    source_label: str,
    source_index: int,
) -> None:
    if not isinstance(source, dict):
        raise ValueError(f"{source_label} must be a dict")

    source_text = _source_text(source)
    if not source_text:
        raise ValueError(f"{source_label} must be narrowly relevant to the current requirement slice")

    lowered = source_text.lower()
    if any(term in lowered for term in _GENERIC_SOURCE_TERMS):
        raise ValueError(f"{source_label} must be narrowly relevant to the current requirement slice")

    requirement_tokens = _requirement_tokens(requirement_statement)
    if not any(token in lowered for token in requirement_tokens) and not any(anchor in lowered for anchor in _SOURCE_RELEVANCE_ANCHORS):
        raise ValueError(f"{source_label} must be narrowly relevant to the current requirement slice")

    if source_index < 0:
        raise ValueError(f"{source_label} index must be non-negative")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalize_conversation(conversation: Any) -> str:
    if isinstance(conversation, str):
        return conversation.strip()
    if isinstance(conversation, list):
        parts: list[str] = []
        for item in conversation:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    parts.append(cleaned)
            elif isinstance(item, dict):
                for key in ("text", "content", "message", "summary"):
                    if key in item and item[key]:
                        cleaned = _normalize_text(item[key])
                        if cleaned:
                            parts.append(cleaned)
                        break
            else:
                cleaned = _normalize_text(item)
                if cleaned:
                    parts.append(cleaned)
        return "\n".join(parts)
    return _normalize_text(conversation)


def _classify_progression_level(
    *,
    requirement_statement: str,
    conversation_text: str,
    admissible_sources: list[tuple[str, int, dict]],
) -> str:
    haystack = f"{requirement_statement}\n{conversation_text}".lower()
    if _contains_signal(
        haystack,
        (
            "design kickoff",
            "handoff to tech lead",
            "tech lead",
            "stable enough for design",
            "ready for design",
            "prd handoff ready",
        ),
    ):
        return "prd_handoff_ready_seed"
    if admissible_sources or _contains_signal(
        haystack,
        (
            "prd seed",
            "shape the prd",
            "shape a prd",
            "clear enough",
            "materially clearer",
            "continue pm-led refinement",
            "pm-led refinement",
        ),
    ):
        return "brief_plus_prd_seed"
    return "brief_only"


def _contains_signal(text: str, signals: tuple[str, ...]) -> bool:
    return any(signal in text for signal in signals)


def _build_evidence_backed_facts(
    *,
    requirement_statement: str,
    conversation_text: str,
    admissible_sources: list[tuple[str, int, dict]],
) -> list[dict]:
    facts = [
        {
            "text": f"Current requirement statement: {requirement_statement}",
            "provenance": {"kind": "conversation", "source": "intent.current_requirement_statement"},
        },
        {
            "text": f"Conversation statement: {conversation_text}",
            "provenance": {"kind": "conversation", "source": "conversation"},
        },
    ]
    for source_label, source_index, source in admissible_sources:
        facts.append(
            {
                "text": _source_fact_text(source_label, source, source_index),
                "provenance": {
                    "kind": source_label,
                    "source_index": source_index,
                    "source_title": _source_title(source),
                },
            }
        )
    return facts


def _build_derived_inferences(
    *,
    progression_level: str,
    requirement_statement: str,
    admissible_sources: list[tuple[str, int, dict]],
) -> list[dict]:
    if progression_level == "brief_only":
        return [
            {
                "text": "The requirement should stay at brief_only until admissible source evidence is available.",
                "provenance": {
                    "kind": "derived",
                    "rule": "progression_classification",
                    "based_on": ["intent.current_requirement_statement", "conversation"],
                },
            },
            {
                "text": "The current slice still needs explicit success criteria and a business target.",
                "provenance": {
                    "kind": "derived",
                    "rule": "missing_evidence_projection",
                    "based_on": ["progression_level=brief_only"],
                },
            },
        ]

    if progression_level == "brief_plus_prd_seed":
        source_bases = ["intent.current_requirement_statement", "conversation"]
        if any(source_label == "primary_source" for source_label, _, _ in admissible_sources):
            source_bases.append("primary_source")
        supporting_count = sum(1 for source_label, _, _ in admissible_sources if source_label == "supporting_source")
        if supporting_count:
            source_bases.append(f"supporting_sources[1..{supporting_count}]")
        return [
            {
                "text": "The requirement should progress to brief_plus_prd_seed because the slice is narrow and supported.",
                "provenance": {
                    "kind": "derived",
                    "rule": "progression_classification",
                    "based_on": source_bases,
                },
            },
            {
                "text": "The current slice is stable enough to begin PRD shaping.",
                "provenance": {
                    "kind": "derived",
                    "rule": "progression_depth",
                    "based_on": ["progression_level=brief_plus_prd_seed"],
                },
            },
            {
                "text": f"Supporting sources reinforce the current requirement slice for: {requirement_statement.rstrip('.!?')}",
                "provenance": {
                    "kind": "derived",
                    "rule": "supporting_sources",
                    "based_on": [
                        "supporting_sources[1..%d]" % max(len(admissible_sources) - 1, 0),
                    ],
                },
            },
        ]

    return [
        {
            "text": "The requirement is stable enough to hand off into design kickoff.",
            "provenance": {
                "kind": "derived",
                "rule": "progression_classification",
                "based_on": ["intent.current_requirement_statement", "conversation"],
            },
        },
        {
            "text": "The current slice can seed design work without pretending execution is ready.",
            "provenance": {
                "kind": "derived",
                "rule": "handoff_depth",
                "based_on": ["progression_level=prd_handoff_ready_seed"],
            },
        },
    ]


def _build_missing_evidence(progression_level: str) -> list[dict]:
    if progression_level == "brief_only":
        return [
            {
                "text": "Specific success criteria",
                "provenance": {"kind": "missing", "needed_for": "brief_plus_prd_seed"},
            },
            {
                "text": "Primary business target or user owner",
                "provenance": {"kind": "missing", "needed_for": "brief_plus_prd_seed"},
            },
            {
                "text": "A narrowly relevant source that constrains the current slice",
                "provenance": {"kind": "missing", "needed_for": "brief_plus_prd_seed"},
            },
        ]

    if progression_level == "brief_plus_prd_seed":
        return [
            {
                "text": "Design kickoff readiness",
                "provenance": {"kind": "missing", "needed_for": "prd_handoff_ready_seed"},
            },
            {
                "text": "Technical constraints and integration boundaries",
                "provenance": {"kind": "missing", "needed_for": "prd_handoff_ready_seed"},
            },
        ]

    return [
        {
            "text": "Implementation sequencing detail",
            "provenance": {"kind": "missing", "needed_for": "execution_plan"},
        },
        {
            "text": "Test and release planning detail",
            "provenance": {"kind": "missing", "needed_for": "execution_plan"},
        },
    ]


def _build_brief_draft(
    *,
    requirement_statement: str,
    progression_level: str,
    admissible_sources: list[tuple[str, int, dict]],
) -> dict:
    scope = ["Bootstrap the current requirement slice from conversation-first input."]
    constraints = ["Keep evidence, inference, and missing evidence separate."]
    key_risks = ["Unsupported guesses can be mistaken for facts."]

    if progression_level == "brief_only":
        constraints.append("Do not imply design readiness.")
        key_risks.append("The slice may still need PM-led clarification before design.")
    else:
        scope.append("Use only narrowly relevant supporting sources.")

    if any(source_label == "primary_source" for source_label, _, _ in admissible_sources):
        scope.append("Honor the explicit primary source as the strongest slice constraint.")

    return {
        "problem": f"Current requirement slice: {requirement_statement}",
        "goals": [requirement_statement],
        "scope": scope,
        "constraints": constraints,
        "key_risks": key_risks,
        "immediate_delivery_intent": _brief_delivery_intent(progression_level),
    }


def _brief_delivery_intent(progression_level: str) -> str:
    if progression_level == "prd_handoff_ready_seed":
        return "Hand the slice to tech_lead for design kickoff."
    if progression_level == "brief_plus_prd_seed":
        return "Continue PM-led refinement and PRD shaping."
    return "Continue clarification before PRD shaping."


def _build_prd_seed_draft(
    *,
    requirement_statement: str,
    progression_level: str,
    conversation_text: str,
    admissible_sources: list[tuple[str, int, dict]],
) -> dict:
    if progression_level == "prd_handoff_ready_seed":
        acceptance_criteria = [
            "The seeded PRD reflects the current requirement slice.",
            "The PRD seed is ready for design kickoff.",
        ]
        rationale = "The current evidence is stable enough to seed design work."
        scope_out = ["Execution detail", "Test plan detail", "Release plan detail"]
    else:
        acceptance_criteria = [
            "The seeded PRD reflects the current requirement slice.",
            "The PRD seed is ready for PM-led refinement.",
        ]
        if "?" in conversation_text:
            acceptance_criteria.append("Open questions remain visible instead of being collapsed into assumptions.")
        rationale = "The current slice has enough evidence to begin structured PRD shaping."
        scope_out = ["Full design spec", "Execution plan", "Release packaging"]

    return {
        "user_scenarios": [requirement_statement],
        "scope_in": [requirement_statement],
        "scope_out": scope_out,
        "acceptance_criteria": acceptance_criteria,
        "rationale": rationale,
    }


def _build_scope_assumptions(
    *,
    progression_level: str,
    primary_source: Any,
    supporting_sources: list[Any],
) -> list[dict]:
    assumptions = [
        {
            "text": "The current conversation is the primary source of truth.",
            "provenance": {"kind": "bootstrap_rule", "source": "conversation"},
        }
    ]
    if primary_source is not None:
        assumptions.append(
            {
                "text": "The primary source constrains this specific requirement slice.",
                "provenance": {"kind": "bootstrap_rule", "source": "primary_source"},
            }
        )
    if supporting_sources:
        assumptions.append(
            {
                "text": "Supporting sources are narrowly relevant to the active requirement slice.",
                "provenance": {"kind": "bootstrap_rule", "source": "supporting_sources"},
            }
        )
    if progression_level == "brief_only":
        assumptions.append(
            {
                "text": "Scope is still tentative and may change with clarification.",
                "provenance": {"kind": "bootstrap_rule", "source": "progression_level=brief_only"},
            }
        )
    return assumptions


def _build_open_questions(progression_level: str) -> list[dict]:
    if progression_level == "brief_only":
        return [
            {"text": "What exact outcome is the team trying to reach now?", "status": "open", "priority": "high"},
            {"text": "What constraints must the baseline respect?", "status": "open", "priority": "high"},
            {"text": "Who is the primary target user or business owner?", "status": "open", "priority": "medium"},
        ]
    if progression_level == "brief_plus_prd_seed":
        return [
            {
                "text": "What remaining technical constraints should the PRD seed carry forward?",
                "status": "open",
                "priority": "high",
            },
            {
                "text": "What evidence would be needed before design kickoff?",
                "status": "open",
                "priority": "medium",
            },
        ]
    return [
        {"text": "What implementation sequencing should the tech lead confirm first?", "status": "open", "priority": "high"},
        {"text": "What test and release details still need explicit ownership?", "status": "open", "priority": "medium"},
    ]


def _build_follow_up_questions(progression_level: str) -> list[dict]:
    if progression_level == "brief_only":
        return [
            {
                "id": "success_criteria",
                "text": "What specific success criteria should define this slice?",
                "priority": "high",
            },
            {
                "id": "primary_owner",
                "text": "Who is the primary user or business owner for this slice?",
                "priority": "high",
            },
            {
                "id": "slice_evidence",
                "text": "What narrowly relevant source can constrain this requirement slice?",
                "priority": "medium",
            },
        ]
    if progression_level == "brief_plus_prd_seed":
        return [
            {
                "id": "design_constraints",
                "text": "What technical constraints or integration boundaries should the PRD carry into design?",
                "priority": "high",
            },
            {
                "id": "design_kickoff_evidence",
                "text": "What evidence is still missing before design kickoff?",
                "priority": "medium",
            },
        ]
    return [
        {
            "id": "design_owner",
            "text": "Who will own the first solution design for this slice?",
            "priority": "medium",
        },
        {
            "id": "design_focus",
            "text": "Which requirement or risk should the first design pass resolve first?",
            "priority": "medium",
        },
    ]


def _eligible_next_artifact_types(progression_level: str) -> list[str]:
    if progression_level == "brief_only":
        return ["brief"]
    if progression_level == "brief_plus_prd_seed":
        return ["brief", "prd_story_pack"]
    return ["brief", "prd_story_pack", "solution_design"]


def _build_next_handoff_recommendation(progression_level: str) -> dict:
    if progression_level == "prd_handoff_ready_seed":
        return {
            "role": "tech_lead",
            "action": "handoff_for_design_kickoff",
            "reason": "The slice is stable enough to seed design work.",
            "progression_level": progression_level,
        }
    if progression_level == "brief_plus_prd_seed":
        return {
            "role": "pm",
            "action": "continue_prd_shaping",
            "reason": "The slice is ready for PM-led refinement before design kickoff.",
            "progression_level": progression_level,
        }
    return {
        "role": "pm",
        "action": "continue_clarification",
        "reason": "The slice still needs clarification before PRD shaping.",
        "progression_level": progression_level,
    }


def _requirement_tokens(requirement_statement: str) -> set[str]:
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", requirement_statement.lower()):
        if len(token) >= 4 and token not in _REQUIREMENT_STOPWORDS:
            tokens.add(token)
    return tokens


def _source_text(source: dict) -> str:
    parts: list[str] = []
    for key in ("title", "summary", "content", "body", "description", "notes"):
        value = source.get(key)
        if value:
            cleaned = _normalize_text(value)
            if cleaned:
                parts.append(cleaned)
    return " ".join(parts).strip()


def _source_title(source: dict) -> str:
    for key in ("title", "name", "summary", "id"):
        value = source.get(key)
        if value:
            return _normalize_text(value)
    return "source"


def _source_fact_text(source_label: str, source: dict, source_index: int) -> str:
    title = _source_title(source)
    if source_label == "primary_source":
        return f"Primary source: {title}"
    return f"Supporting source {source_index}: {title}"


def _normalize_materialization_seed(seed: dict, *, workspace_name: str) -> dict:
    progression_level = seed.get("progression_level", "brief_only")
    brief_payload = _normalize_artifact_payload(
        seed.get("brief_draft"),
        artifact_type="brief",
        workspace_name=workspace_name,
    )
    prd_draft = seed.get("prd_seed_draft")
    prd_payload = None
    if progression_level != "brief_only" or prd_draft is not None:
        prd_payload = _normalize_artifact_payload(
            prd_draft,
            artifact_type="prd_story_pack",
            workspace_name=workspace_name,
        )
    return {
        "progression_level": progression_level,
        "brief": brief_payload,
        "prd": prd_payload,
    }


def _normalize_artifact_payload(
    draft: Any,
    *,
    artifact_type: str,
    workspace_name: str,
) -> dict:
    if not isinstance(draft, dict):
        draft = {}

    feature_key = _normalize_feature_key(workspace_name)
    starter_scope = {
        "product_area": "bootstrap",
        "feature_key": feature_key,
    }
    explicit_scope = draft.get("scope", {})
    scope = dict(starter_scope)
    if isinstance(explicit_scope, dict):
        scope.update(explicit_scope)
    scope.setdefault("feature_key", feature_key)

    payload = {
        "artifact_id": draft.get("artifact_id") or _derive_artifact_id(artifact_type, feature_key),
        "title": draft.get("title") or _derive_artifact_title(artifact_type, feature_key),
        "summary": draft.get("summary") or _derive_artifact_summary(artifact_type, draft),
        "status": draft.get("status", "in_review"),
        "version": draft.get("version", "v0.1"),
        "scope": scope,
        "body_markdown": draft.get("body_markdown") or _render_seed_markdown(draft, artifact_type),
    }
    return payload


def _build_materialized_header(existing_header: dict, payload: dict, *, artifact_type: str) -> dict:
    header = deepcopy(existing_header)
    header["artifact_id"] = payload["artifact_id"]
    header["artifact_type"] = artifact_type
    header["title"] = payload["title"]
    header["summary"] = payload["summary"]
    header["status"] = payload["status"]
    header["version"] = payload["version"]
    existing_scope = header.get("scope", {})
    merged_scope = dict(existing_scope) if isinstance(existing_scope, dict) else {}
    merged_scope.update(payload["scope"])
    header["scope"] = merged_scope
    return header


def _build_materialized_body(payload: dict, *, seed: dict, artifact_type: str, include_bootstrap_context: bool) -> str:
    body = str(payload["body_markdown"]).strip()
    if not include_bootstrap_context:
        return _ensure_artifact_body_valid(
            f"{body}\n" if body else "",
            artifact_type=artifact_type,
            payload=payload,
        )

    sections = [body] if body else []
    evidence_map = seed.get("evidence_map")
    if isinstance(evidence_map, dict):
        sections.append(_render_bootstrap_list_section("Bootstrap Evidence", evidence_map.get("evidence_backed_facts", [])))
        sections.append(_render_bootstrap_list_section("Derived Inferences", evidence_map.get("derived_inferences", [])))
        sections.append(_render_bootstrap_list_section("Missing Evidence", evidence_map.get("missing_evidence", [])))
    sections.append(_render_bootstrap_list_section("Scope Assumptions", seed.get("scope_assumptions", [])))
    sections.append(_render_bootstrap_list_section("Open Questions", seed.get("open_questions", [])))
    handoff = seed.get("next_handoff_recommendation")
    if isinstance(handoff, dict) and handoff:
        sections.append(
            "\n".join(
                [
                    "## Next Handoff Recommendation",
                    "",
                    f"- Role: {handoff.get('role', 'unknown')}",
                    f"- Action: {handoff.get('action', 'unknown')}",
                    f"- Reason: {handoff.get('reason', 'not provided')}",
                ]
            )
        )

    composed = "\n\n".join(section for section in sections if section).rstrip() + "\n"
    return _ensure_artifact_body_valid(
        composed,
        artifact_type=artifact_type,
        payload=payload,
    )


def _render_bootstrap_list_section(title: str, items: Any) -> str:
    normalized_items = _normalize_section_items(items)
    if not normalized_items:
        return ""
    lines = [f"## {title}", ""]
    lines.extend(f"- {item}" for item in normalized_items)
    return "\n".join(lines)


def _normalize_section_items(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []

    normalized: list[str] = []
    for item in items:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                normalized.append(cleaned)
            continue
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                normalized.append(text.strip())
    return normalized


def _rewrite_handoff_refs(brief_header: dict, prd_header: dict, *, brief_artifact_id: str, prd_artifact_id: str) -> None:
    downstream_refs = brief_header.get("downstream_refs")
    if isinstance(downstream_refs, list):
        for ref in downstream_refs:
            if isinstance(ref, dict) and ref.get("target_type") == "prd_story_pack":
                ref["target_id"] = prd_artifact_id

    upstream_refs = prd_header.get("upstream_refs")
    if isinstance(upstream_refs, list):
        for ref in upstream_refs:
            if isinstance(ref, dict) and ref.get("target_type") == "brief":
                ref["target_id"] = brief_artifact_id


def _validate_materialized_workspace(
    repo_root: Path,
    *,
    brief_header: dict,
    brief_body: str,
    prd_header: dict | None,
    prd_body: str | None,
    schema_path: str | Path,
) -> None:
    schema = load_schema(schema_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        staged_root = Path(temp_dir) / "repo"
        shutil.copytree(repo_root, staged_root)
        write_artifact_document(staged_root / STARTER_BRIEF_FILENAME, brief_header, brief_body)
        if prd_header is not None and prd_body is not None:
            write_artifact_document(staged_root / STARTER_PRD_FILENAME, prd_header, prd_body)
        _rekey_connected_templates(
            staged_root,
            feature_key=brief_header["scope"]["feature_key"],
            brief_artifact_id=brief_header["artifact_id"],
            prd_artifact_id=(prd_header or {}).get("artifact_id", "PRD-TEMPLATE-001"),
        )
        issues = validate_repository(load_repository([staged_root]), schema)
    if issues:
        first_issue = issues[0]
        raise ValueError(f"{first_issue.code}: {first_issue.message}")

    _rekey_connected_templates(
        repo_root,
        feature_key=brief_header["scope"]["feature_key"],
        brief_artifact_id=brief_header["artifact_id"],
        prd_artifact_id=(prd_header or {}).get("artifact_id", "PRD-TEMPLATE-001"),
    )


def _normalize_feature_key(workspace_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", workspace_name.lower()).strip("-")
    return normalized or "bootstrap-slice"


def _derive_artifact_id(artifact_type: str, feature_key: str) -> str:
    prefix = "BRIEF" if artifact_type == "brief" else "PRD"
    stable_key = feature_key.upper().replace("-", "_")
    return f"{prefix}-BOOTSTRAP-{stable_key}"


def _derive_artifact_title(artifact_type: str, feature_key: str) -> str:
    label = feature_key.replace("-", " ").title()
    suffix = "Brief" if artifact_type == "brief" else "PRD"
    return f"{label} {suffix}".strip()


def _derive_artifact_summary(artifact_type: str, draft: dict) -> str:
    if artifact_type == "brief":
        return _normalize_text(draft.get("immediate_delivery_intent")) or "Bootstrap the current requirement slice."
    return _normalize_text(draft.get("rationale")) or "Seed the current requirement slice into a governed PRD baseline."


def _render_seed_markdown(draft: dict, artifact_type: str) -> str:
    if artifact_type == "brief":
        return _render_brief_seed_markdown(draft)
    return _render_prd_seed_markdown(draft)


def _render_brief_seed_markdown(draft: dict) -> str:
    sections = [
        _render_markdown_section("Background", [draft.get("problem")]),
        _render_markdown_section("Goals", draft.get("goals", [])),
        _render_markdown_section("Scope", draft.get("scope", [])),
        _render_markdown_section("Constraints", draft.get("constraints", [])),
        _render_markdown_section("Key Risks", draft.get("key_risks", [])),
    ]
    immediate_intent = _normalize_text(draft.get("immediate_delivery_intent"))
    if immediate_intent:
        sections.append("\n".join(["## Immediate Delivery Intent", "", immediate_intent]))
    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def _render_prd_seed_markdown(draft: dict) -> str:
    sections = [
        _render_markdown_section("User Scenarios", draft.get("user_scenarios", [])),
        _render_markdown_section("Scope In", draft.get("scope_in", [])),
        _render_markdown_section("Scope Out", draft.get("scope_out", [])),
        _render_markdown_section("Acceptance Criteria", draft.get("acceptance_criteria", [])),
    ]
    rationale = _normalize_text(draft.get("rationale"))
    if rationale:
        sections.append("\n".join(["## Rationale", "", rationale]))
    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def _render_markdown_section(title: str, items: Any) -> str:
    normalized_items = _normalize_section_items(items if isinstance(items, list) else [items])
    if not normalized_items:
        return ""
    lines = [f"## {title}", ""]
    lines.extend(f"- {item}" for item in normalized_items)
    return "\n".join(lines)


def _ensure_artifact_body_valid(body: str, *, artifact_type: str, payload: dict) -> str:
    normalized_headings = {_normalize_heading_name(match) for match in re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)}
    sections = [body.strip()] if body.strip() else []
    for title in REQUIRED_SECTION_TITLES[artifact_type]:
        if _normalize_heading_name(title) in normalized_headings:
            continue
        sections.append(_default_required_section(title, artifact_type=artifact_type, payload=payload))

    sections.append("## Trace Units\n\n" + render_yaml_block(_build_minimum_trace_units(artifact_type, payload)).strip())
    sections.append("## Relation Edges\n\n" + render_yaml_block(_build_minimum_relation_edges(artifact_type, payload)).strip())
    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def _normalize_heading_name(title: str) -> str:
    lowered = title.replace("_", " ").lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def _default_required_section(title: str, *, artifact_type: str, payload: dict) -> str:
    scope = payload.get("scope", {})
    in_scope = scope.get("in_scope", []) if isinstance(scope, dict) else []
    out_of_scope = scope.get("out_of_scope", []) if isinstance(scope, dict) else []
    summary = payload.get("summary", "Clarify the current requirement slice.")
    defaults = {
        "brief": {
            "Background": summary,
            "Problem Statement": summary,
            "Target Users": "- Product, engineering, and QA collaborators",
            "Goals": f"- {summary}",
            "Success Metrics": "- Reviewers can align on one governed baseline.",
            "Non-goals": "- Full execution and release planning in this phase.",
        },
        "prd_story_pack": {
            "User Scenarios": f"- {payload.get('title', 'Current requirement slice')} is shaped into a reviewable PRD baseline.",
            "Scope In": _render_bullet_lines(in_scope) or f"- {summary}",
            "Scope Out": _render_bullet_lines(out_of_scope) or "- Detailed execution and release packaging.",
            "Functional Requirements": f"- {summary}",
            "Edge Cases": "- Missing scope boundaries\n- Incomplete reviewer alignment",
            "Acceptance Criteria": "- The PRD baseline is reviewable and can hand off into design.",
        },
    }
    content = defaults[artifact_type][title]
    return f"## {title}\n\n{content}"


def _render_bullet_lines(items: Any) -> str:
    normalized = _normalize_section_items(items)
    if not normalized:
        return ""
    return "\n".join(f"- {item}" for item in normalized)


def _build_minimum_trace_units(artifact_type: str, payload: dict) -> list[dict]:
    title = payload.get("title", "Bootstrap baseline")
    summary = payload.get("summary", "Bootstrap the current requirement slice.")
    if artifact_type == "brief":
        return [
            {
                "id": "GOAL-001",
                "type": "GOAL",
                "title": title,
                "statement": summary,
                "status": "proposed",
                "priority": "high",
                "success_measure": "The team can review and continue the baseline without re-deriving core context.",
            }
        ]
    return [
        {
            "id": "REQ-001",
            "type": "REQ",
            "title": title,
            "statement": summary,
            "status": "proposed",
            "priority": "high",
            "rationale": "The requirement baseline must stay reviewable and governed.",
        },
        {
            "id": "AC-001",
            "type": "AC",
            "title": f"{title} acceptance",
            "statement": "The PRD baseline is specific enough for design kickoff discussion.",
            "status": "proposed",
            "priority": "high",
            "verification_hint": "Confirm PM, engineering, and QA can review the same PRD baseline.",
        },
    ]


def _build_minimum_relation_edges(artifact_type: str, payload: dict) -> list[dict]:
    if artifact_type == "brief":
        return []
    brief_artifact_id = payload.get("upstream_brief_artifact_id", "BRIEF-TEMPLATE-001")
    prd_artifact_id = payload.get("artifact_id", "PRD-TEMPLATE-001")
    return [
        {
            "edge_id": "EDGE-0001",
            "relation_type": "refines",
            "from": {
                "id": "GOAL-001",
                "kind": "trace_unit",
                "artifact_id": brief_artifact_id,
                "type": "GOAL",
            },
            "to": {
                "id": "REQ-001",
                "kind": "trace_unit",
                "artifact_id": prd_artifact_id,
                "type": "REQ",
            },
        },
        {
            "edge_id": "EDGE-0002",
            "relation_type": "refines",
            "from": {
                "id": "REQ-001",
                "kind": "trace_unit",
                "artifact_id": prd_artifact_id,
                "type": "REQ",
            },
            "to": {
                "id": "AC-001",
                "kind": "trace_unit",
                "artifact_id": prd_artifact_id,
                "type": "AC",
            },
        },
    ]


def _rekey_connected_templates(
    repo_root: Path,
    *,
    feature_key: str,
    brief_artifact_id: str,
    prd_artifact_id: str,
) -> None:
    replacements = {
        "starter-feature": feature_key,
        "BRIEF-TEMPLATE-001": brief_artifact_id,
        "PRD-TEMPLATE-001": prd_artifact_id,
    }
    for relative_path in CONNECTED_TEMPLATE_FILENAMES:
        artifact_path = repo_root / relative_path
        if not artifact_path.is_file():
            continue
        header, body = read_artifact_parts(artifact_path)
        scope = header.get("scope")
        if isinstance(scope, dict):
            scope["feature_key"] = feature_key
        for field_name in ("upstream_refs", "downstream_refs"):
            refs = header.get(field_name)
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if not isinstance(ref, dict):
                    continue
                target_id = ref.get("target_id")
                if target_id in replacements:
                    ref["target_id"] = replacements[target_id]
        updated_body = body
        for source, target in replacements.items():
            updated_body = updated_body.replace(source, target)
        write_artifact_document(artifact_path, header, updated_body)


def _load_optional_template_artifact_header(artifact_path: Path, template_filename: str) -> dict:
    if artifact_path.is_file():
        header, _ = read_artifact_parts(artifact_path)
        return header

    template_path = Path(__file__).resolve().parents[1] / "templates" / STARTER_TEMPLATE_DIRNAME / template_filename
    header, _ = read_artifact_parts(template_path)
    if template_filename == STARTER_PRD_FILENAME:
        header = deepcopy(header)
        header.pop("downstream_refs", None)
    return header
