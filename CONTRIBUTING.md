# Contributing Guide

## Branching
- Main integration branch per version: release/vX.Y
- Feature branches should be created from release/vX.Y:
  - feat/REQ-<id>-<slug>
  - fix/REQ-<id>-<slug>
  - docs/REQ-<id>-<slug>

## PR Targets
- Feature/fix/docs PRs -> release/vX.Y
- Release closure PR -> main

## Requirement Intake
- Add/update requirement in Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
- Ensure acceptance criteria are testable

## Regression Policy
- Mandatory before merge: python run_ci_tests.py
- Add targeted tests when behavior changes

## Documentation Policy
- Update at least one of:
  - Documentation/Project/Releases/CHANGELOG.md
  - Documentation/Project/Releases/vX.Y.Z.md
  - Documentation/Project/Traceability/REQUIREMENTS_TO_TESTS.md

## Release Steps
1. Freeze release/vX.Y
2. Run full regression
3. Finalize release notes and changelog
4. Merge release/vX.Y -> main
5. Create git tag and GitHub release
