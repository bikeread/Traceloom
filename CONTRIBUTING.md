# Contributing to Traceloom

Traceloom is currently in a public beta phase.
Contributions are welcome, but changes should preserve the repository's core constraints:

- keep the canonical artifact model Git-native and schema-first
- keep MCP behavior role-neutral unless a design doc explicitly says otherwise
- prefer additive changes with regression coverage over broad refactors

## Before you open a change

- open an issue for bug reports, missing docs, or feature proposals when the change is not obviously small
- explain the user problem, not just the implementation idea
- link any relevant design or roadmap document when changing product shape or protocol behavior

## Development workflow

1. Create a branch from the latest `main`.
2. Make the smallest coherent change that solves one problem.
3. Add or update tests before changing runtime behavior.
4. Run the relevant verification commands locally.
5. Open a pull request with context, risks, and verification notes.

## Local verification

Use the narrowest command that proves your change, then run broader checks when appropriate.

```bash
pytest -q
python -m traceloom validate examples/user-tag-bulk-import
python -m traceloom mcp --paths examples/user-tag-bulk-import --print-tools
```

## Pull request expectations

- describe the user-visible outcome
- call out schema, MCP, or example-fixture impact explicitly
- include the exact verification commands you ran
- keep docs aligned when the public surface changes

## Code and review norms

- follow the existing repository structure and naming patterns
- avoid unrelated cleanup in the same pull request
- prefer deterministic fixtures and reproducible tests
- be ready to narrow scope if a change mixes product decisions with implementation work

## Security

Do not open public issues for undisclosed security problems.
Follow the reporting guidance in [SECURITY.md](SECURITY.md).
