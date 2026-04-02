from __future__ import annotations

import unittest


def import_bootstrap_runtime():
    try:
        from traceloom.bootstrap import apply_bootstrap_seed_to_workspace, prepare_requirement_bootstrap
        from traceloom.workspaces import create_workspace_from_starter
    except ImportError as exc:
        raise AssertionError(f"could not import bootstrap runtime: {exc}") from exc
    return prepare_requirement_bootstrap, apply_bootstrap_seed_to_workspace, create_workspace_from_starter


class RequirementBootstrapTests(unittest.TestCase):
    def test_prepare_requirement_bootstrap_builds_brief_only_seed_from_conversation_only_request(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        payload = prepare_requirement_bootstrap(
            {
                "intent": {
                    "current_requirement_statement": "Clarify the current onboarding requirement slice.",
                    "target_user": "operations",
                    "target_outcome": "brief",
                },
                "conversation": "We are still defining the requirement and need to clarify the baseline before any PRD work.",
            }
        )

        self.assertEqual(payload["progression_level"], "brief_only")
        self.assertEqual(
            payload["evidence_map"],
            {
                "evidence_backed_facts": [
                    {
                        "text": "Current requirement statement: Clarify the current onboarding requirement slice.",
                        "provenance": {"kind": "conversation", "source": "intent.current_requirement_statement"},
                    },
                    {
                        "text": "Conversation statement: We are still defining the requirement and need to clarify the baseline before any PRD work.",
                        "provenance": {"kind": "conversation", "source": "conversation"},
                    },
                ],
                "derived_inferences": [
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
                ],
                "missing_evidence": [
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
                ],
            },
        )
        self.assertEqual(
            payload["scope_assumptions"],
            [
                {
                    "text": "The current conversation is the primary source of truth.",
                    "provenance": {"kind": "bootstrap_rule", "source": "conversation"},
                },
                {
                    "text": "Scope is still tentative and may change with clarification.",
                    "provenance": {"kind": "bootstrap_rule", "source": "progression_level=brief_only"},
                },
            ],
        )
        self.assertEqual(
            payload["open_questions"],
            [
                {
                    "text": "What exact outcome is the team trying to reach now?",
                    "status": "open",
                    "priority": "high",
                },
                {
                    "text": "What constraints must the baseline respect?",
                    "status": "open",
                    "priority": "high",
                },
                {
                    "text": "Who is the primary target user or business owner?",
                    "status": "open",
                    "priority": "medium",
                },
            ],
        )
        self.assertEqual(
            payload["next_handoff_recommendation"],
            {
                "role": "pm",
                "action": "continue_clarification",
                "reason": "The slice still needs clarification before PRD shaping.",
                "progression_level": "brief_only",
            },
        )
        self.assertEqual(
            payload["follow_up_questions"],
            [
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
            ],
        )
        self.assertEqual(payload["eligible_next_artifact_types"], ["brief"])
        self.assertEqual(
            payload["brief_draft"],
            {
                "problem": "Current requirement slice: Clarify the current onboarding requirement slice.",
                "goals": ["Clarify the current onboarding requirement slice."],
                "scope": [
                    "Bootstrap the current requirement slice from conversation-first input.",
                ],
                "constraints": [
                    "Keep evidence, inference, and missing evidence separate.",
                    "Do not imply design readiness.",
                ],
                "key_risks": [
                    "Unsupported guesses can be mistaken for facts.",
                    "The slice may still need PM-led clarification before design.",
                ],
                "immediate_delivery_intent": "Continue clarification before PRD shaping.",
            },
        )
        self.assertNotIn("prd_seed_draft", payload)

    def test_prepare_requirement_bootstrap_includes_prd_seed_when_slice_is_clear_enough(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        payload = prepare_requirement_bootstrap(
            {
                "intent": {
                    "current_requirement_statement": "Shape the PRD seed for the onboarding slice.",
                    "target_user": "operations",
                    "target_outcome": "prd seed",
                },
                "conversation": "The scope is clear enough to shape a PRD seed and continue PM-led refinement.",
                "primary_source": {
                    "title": "Current onboarding notes",
                    "summary": "A small source that directly constrains the requirement slice.",
                },
                "supporting_sources": [
                    {"title": "Ticket 1", "summary": "Confirms the current requirement."},
                    {"title": "Ticket 2", "summary": "Adds a supporting constraint."},
                ],
            }
        )

        self.assertEqual(payload["progression_level"], "brief_plus_prd_seed")
        self.assertEqual(
            payload["evidence_map"],
            {
                "evidence_backed_facts": [
                    {
                        "text": "Current requirement statement: Shape the PRD seed for the onboarding slice.",
                        "provenance": {"kind": "conversation", "source": "intent.current_requirement_statement"},
                    },
                    {
                        "text": "Conversation statement: The scope is clear enough to shape a PRD seed and continue PM-led refinement.",
                        "provenance": {"kind": "conversation", "source": "conversation"},
                    },
                    {
                        "text": "Primary source: Current onboarding notes",
                        "provenance": {
                            "kind": "primary_source",
                            "source_index": 0,
                            "source_title": "Current onboarding notes",
                        },
                    },
                    {
                        "text": "Supporting source 1: Ticket 1",
                        "provenance": {
                            "kind": "supporting_source",
                            "source_index": 1,
                            "source_title": "Ticket 1",
                        },
                    },
                    {
                        "text": "Supporting source 2: Ticket 2",
                        "provenance": {
                            "kind": "supporting_source",
                            "source_index": 2,
                            "source_title": "Ticket 2",
                        },
                    },
                ],
                "derived_inferences": [
                    {
                        "text": "The requirement should progress to brief_plus_prd_seed because the slice is narrow and supported.",
                        "provenance": {
                            "kind": "derived",
                            "rule": "progression_classification",
                            "based_on": [
                                "intent.current_requirement_statement",
                                "conversation",
                                "primary_source",
                                "supporting_sources[1..2]",
                            ],
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
                        "text": "Supporting sources reinforce the current requirement slice for: Shape the PRD seed for the onboarding slice",
                        "provenance": {
                            "kind": "derived",
                            "rule": "supporting_sources",
                            "based_on": ["supporting_sources[1..2]"],
                        },
                    },
                ],
                "missing_evidence": [
                    {
                        "text": "Design kickoff readiness",
                        "provenance": {"kind": "missing", "needed_for": "prd_handoff_ready_seed"},
                    },
                    {
                        "text": "Technical constraints and integration boundaries",
                        "provenance": {"kind": "missing", "needed_for": "prd_handoff_ready_seed"},
                    },
                ],
            },
        )
        self.assertEqual(
            payload["scope_assumptions"],
            [
                {
                    "text": "The current conversation is the primary source of truth.",
                    "provenance": {"kind": "bootstrap_rule", "source": "conversation"},
                },
                {
                    "text": "The primary source constrains this specific requirement slice.",
                    "provenance": {"kind": "bootstrap_rule", "source": "primary_source"},
                },
                {
                    "text": "Supporting sources are narrowly relevant to the active requirement slice.",
                    "provenance": {"kind": "bootstrap_rule", "source": "supporting_sources"},
                },
            ],
        )
        self.assertEqual(
            payload["open_questions"],
            [
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
            ],
        )
        self.assertEqual(
            payload["next_handoff_recommendation"],
            {
                "role": "pm",
                "action": "continue_prd_shaping",
                "reason": "The slice is ready for PM-led refinement before design kickoff.",
                "progression_level": "brief_plus_prd_seed",
            },
        )
        self.assertEqual(
            payload["follow_up_questions"],
            [
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
            ],
        )
        self.assertEqual(payload["eligible_next_artifact_types"], ["brief", "prd_story_pack"])
        self.assertIn("prd_seed_draft", payload)
        self.assertEqual(
            payload["prd_seed_draft"],
            {
                "user_scenarios": ["Shape the PRD seed for the onboarding slice."],
                "scope_in": ["Shape the PRD seed for the onboarding slice."],
                "scope_out": ["Full design spec", "Execution plan", "Release packaging"],
                "acceptance_criteria": [
                    "The seeded PRD reflects the current requirement slice.",
                    "The PRD seed is ready for PM-led refinement.",
                ],
                "rationale": "The current slice has enough evidence to begin structured PRD shaping.",
            },
        )

    def test_prepare_requirement_bootstrap_reaches_prd_handoff_ready_seed_for_design_kickoff_language(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        payload = prepare_requirement_bootstrap(
            {
                "intent": {
                    "current_requirement_statement": "Prepare the onboarding slice for design kickoff.",
                    "target_user": "engineering",
                    "target_outcome": "handoff",
                },
                "conversation": "The requirement is stable enough for design kickoff and handoff to tech lead.",
                "primary_source": {
                    "title": "PRD draft",
                    "summary": "Supports the current requirement slice.",
                },
            }
        )

        self.assertEqual(payload["progression_level"], "prd_handoff_ready_seed")
        self.assertEqual(
            payload["next_handoff_recommendation"],
            {
                "role": "tech_lead",
                "action": "handoff_for_design_kickoff",
                "reason": "The slice is stable enough to seed design work.",
                "progression_level": "prd_handoff_ready_seed",
            },
        )
        self.assertEqual(
            payload["follow_up_questions"],
            [
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
            ],
        )
        self.assertEqual(
            payload["eligible_next_artifact_types"],
            ["brief", "prd_story_pack", "solution_design"],
        )
        self.assertEqual(
            payload["prd_seed_draft"]["acceptance_criteria"],
            [
                "The seeded PRD reflects the current requirement slice.",
                "The PRD seed is ready for design kickoff.",
            ],
        )

    def test_prepare_requirement_bootstrap_rejects_opaque_string_intent_contract(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        with self.assertRaises(ValueError) as ctx:
            prepare_requirement_bootstrap(
                {
                    "intent": "shape the PRD seed",
                    "conversation": "Enough conversation to seed the slice.",
                }
            )

        self.assertIn("current_requirement_statement", str(ctx.exception))

    def test_prepare_requirement_bootstrap_rejects_more_than_five_supporting_sources(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        with self.assertRaises(ValueError) as ctx:
            prepare_requirement_bootstrap(
                {
                    "intent": {"current_requirement_statement": "Shape the PRD seed."},
                    "conversation": "Enough conversation to seed the slice.",
                    "supporting_sources": [
                        {"title": "S1", "summary": "Relevant."},
                        {"title": "S2", "summary": "Relevant."},
                        {"title": "S3", "summary": "Relevant."},
                        {"title": "S4", "summary": "Relevant."},
                        {"title": "S5", "summary": "Relevant."},
                        {"title": "S6", "summary": "Relevant."},
                    ],
                }
            )

        self.assertIn("up to five supporting sources", str(ctx.exception))

    def test_prepare_requirement_bootstrap_rejects_generic_background_sources(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        with self.assertRaises(ValueError) as ctx:
            prepare_requirement_bootstrap(
                {
                    "intent": {"current_requirement_statement": "Shape the PRD seed for the onboarding slice."},
                    "conversation": "The scope is clear enough to shape a PRD seed.",
                    "primary_source": {
                        "title": "Company overview",
                        "summary": "High-level background about the company.",
                    },
                }
            )

        self.assertIn("narrowly relevant", str(ctx.exception))

    def test_prepare_requirement_bootstrap_rejects_generic_supporting_background_sources(self):
        prepare_requirement_bootstrap, _, _ = import_bootstrap_runtime()

        with self.assertRaises(ValueError) as ctx:
            prepare_requirement_bootstrap(
                {
                    "intent": {"current_requirement_statement": "Shape the PRD seed for the onboarding slice."},
                    "conversation": "The scope is clear enough to shape a PRD seed.",
                    "supporting_sources": [
                        {
                            "title": "Background notes",
                            "summary": "General background for the product area.",
                        }
                    ],
                }
            )

        self.assertIn("narrowly relevant", str(ctx.exception))

    def test_apply_bootstrap_seed_to_workspace_materializes_brief_and_prd_baseline(self):
        _, apply_bootstrap_seed_to_workspace, create_workspace_from_starter = import_bootstrap_runtime()

        import tempfile

        from traceloom.defaults import resolve_default_schema_path
        from traceloom.repository import load_repository
        from traceloom.validators import load_schema, validate_repository

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = create_workspace_from_starter("billing-intake", root=temp_dir)
            result = apply_bootstrap_seed_to_workspace(
                workspace,
                {
                    "progression_level": "brief_plus_prd_seed",
                    "brief_draft": {
                        "artifact_id": "BRIEF-2026-900",
                        "title": "Retry-Safe Bulk Import Brief",
                        "summary": "Clarify operator-safe retry behavior.",
                        "body_markdown": "## Background\n\nOperators need safe retries.\n",
                        "scope": {
                            "product_area": "growth",
                            "feature_key": "billing-intake",
                            "target_release": "2026.06",
                        },
                    },
                    "prd_seed_draft": {
                        "artifact_id": "PRD-2026-900",
                        "title": "Retry-Safe Bulk Import PRD",
                        "summary": "Define retry-safe import requirements.",
                        "body_markdown": "## Requirements\n\n- Prevent duplicate writes.\n",
                        "scope": {
                            "product_area": "growth",
                            "feature_key": "billing-intake",
                            "target_release": "2026.06",
                        },
                    },
                    "evidence_map": {
                        "evidence_backed_facts": ["Operators need safe retries."],
                        "derived_inferences": ["A PRD seed is justified."],
                        "missing_evidence": ["Need confirmation on rollback UX."],
                    },
                    "scope_assumptions": ["No new admin UI in phase 1."],
                    "open_questions": ["Should retries be idempotent across file re-uploads?"],
                    "next_handoff_recommendation": {
                        "role": "pm",
                        "action": "continue_prd_shaping",
                        "reason": "The slice is ready for PM-led refinement before design kickoff.",
                        "progression_level": "brief_plus_prd_seed",
                    },
                },
            )

            self.assertEqual(result["workspace_name"], "billing-intake")
            self.assertEqual(result["created_baseline"]["brief"]["artifact_id"], "BRIEF-2026-900")
            self.assertEqual(result["created_baseline"]["prd"]["artifact_id"], "PRD-2026-900")

            repository = load_repository([workspace.active_repository_path])
            self.assertIn("BRIEF-2026-900", repository.artifacts_by_id)
            self.assertIn("PRD-2026-900", repository.artifacts_by_id)
            self.assertNotIn("BRIEF-TEMPLATE-001", repository.artifacts_by_id)
            self.assertNotIn("PRD-TEMPLATE-001", repository.artifacts_by_id)

            schema = load_schema(resolve_default_schema_path(module_file=__file__))
            issues = validate_repository(repository, schema)

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
