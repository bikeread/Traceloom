# Changelog

All notable changes to Traceloom should be recorded in this file.

## Unreleased

- Added the first companion executable packaging slice:
  packaged schema fallback, bundled demo assets, `mcp --demo`, a committed
  `macOS + Windows` companion build/smoke pipeline, and companion-first
  onboarding docs while the public MCP contract remains read-only.
- Hardened the public-beta outsider path so docs and CI now prefer the
  installed `traceloom` CLI, keep `python -m traceloom` as fallback-only,
  and smoke the installed console script in CI while the public MCP contract
  remains read-only.
- Added the open-source governance baseline for the public beta facade.
- Added the phase-1 governed write protocol slice for local CLI use:
  `record-review-decision`, `record-validation-result`, and
  `promote-artifact-status` with staged validation while MCP remains read-only.
- Added the phase-2 governed write protocol slice for local CLI use:
  `create-artifact-draft`, `revise-artifact-draft`, and
  `supersede-artifact-version`, plus optional actor `capability` and
  `decision_authority` passthrough on local governed write commands while MCP
  remains read-only.
- Added the first Track B workflow read slice:
  `workflow` on the local CLI plus `get_artifact_workflow` on the public
  read-only MCP surface.
- Added the first Track C guided delivery-slice read surface:
  `navigate-feature` on the local CLI plus `get_delivery_slice_navigation`
  on the public read-only MCP surface for the `PM-first` `brief -> PRD ->
  design` slice, clamped at `design_handoff_ready` and kept
  `guide-and-recommend` only.
- Added the first Track C confirm-and-execute local companion executor slice:
  canonical `guided_action_package` generation plus
  `prepare-guided-action` / `execute-guided-action` on the local CLI for one
  confirmed first-slice governed action at a time, while the public MCP
  contract remains read-only.

## 0.1.0 - 2026-03-24

- Packaged the read-only CLI and MCP runtime baseline.
- Locked the feature-triage, release-triage, and impact-analysis golden paths.
- Shipped example and invalid fixture coverage for the public beta runtime surface.
