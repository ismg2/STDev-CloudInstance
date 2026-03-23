# Requirements Workflow

This file defines the step-by-step process for adding requirements, discussing scope, implementing safely, and releasing.

## End-to-End Loop
1. Add or update a requirement in Planning/REQUIREMENTS_BACKLOG.md.
2. Discuss in chat and decide: select now or defer.
3. If selected, set target version and acceptance criteria.
4. Implement on a feature branch based on release/vX.Y.
5. Run full regression: python run_ci_tests.py.
6. Update traceability files and release notes draft.
7. Open PR to release/vX.Y with checklist completed.
8. After all selected requirements pass, open release/vX.Y -> main PR.
9. Tag and release on GitHub.

## Branching Model
- Integration branch per version: release/vX.Y
- Implementation branches:
  - feat/REQ-<id>-<short-slug>
  - fix/REQ-<id>-<short-slug>
  - docs/REQ-<id>-<short-slug>

## Required Evidence in PR
- Requirement ID(s)
- Acceptance criteria status
- Regression command and summary
- Docs updated paths
- Risk notes and rollback notes

## Regression Gate
- Mandatory command: python run_ci_tests.py
- Optional targeted tests for changed modules
- No merge if full regression fails
