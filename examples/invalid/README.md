# Invalid Fixture Examples

These fixture repositories are intentionally invalid.
Validate each directory on its own rather than loading the whole `examples/invalid/` tree at once.

Included fixtures:

- `trace-unit-id-pattern`: malformed trace-unit ID pattern, expected to surface `invalid_pattern`
- `typed-ref-target-type-mismatch`: header typed-ref target type mismatch, expected to surface `typed_ref_target_type_mismatch`
- `relation-endpoint-type-mismatch`: relation-edge endpoint type mismatch, expected to surface `relation_endpoint_type_mismatch`
- `illegal-status-transition`: invalid state-machine transition in `status_history`, expected to surface `invalid_status_transition`
- `missing-supersedes-link`: versioned artifact family missing an artifact-level `supersedes` link, expected to surface `missing_supersedes_link`
- `supersedes-same-version`: artifact-level `supersedes` links two artifacts with the same version, expected to surface `supersedes_same_version`

Note:

- immutable same-version mutation cases are covered by git-backed regression tests rather than a static committed fixture directory because the validator compares working-tree files against `HEAD`
