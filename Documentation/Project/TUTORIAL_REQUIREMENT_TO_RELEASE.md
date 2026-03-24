# Tutorial: Requirement to Release Workflow

This guide explains exactly how to go from a new idea to implementation, regression testing, PR, and release.

## Table of Contents
- [Tutorial: Requirement to Release Workflow](#tutorial-requirement-to-release-workflow)
  - [Table of Contents](#table-of-contents)
  - [1. Entry Point](#1-entry-point)
  - [2. Files You Will Edit](#2-files-you-will-edit)
  - [3. Step-by-Step Process](#3-step-by-step-process)
    - [Step A - Add a requirement](#step-a---add-a-requirement)
    - [Step B - Decide with Codex](#step-b---decide-with-codex)
    - [Step C - Implement on branch](#step-c---implement-on-branch)
    - [Step D - Run regression](#step-d---run-regression)
    - [Step E - Update traceability and release docs](#step-e---update-traceability-and-release-docs)
    - [Step F - PR to release branch](#step-f---pr-to-release-branch)
    - [Step G - Release close](#step-g---release-close)
  - [4. TODO Tag Convention](#4-todo-tag-convention)
  - [5. Codex Discussion Routine (Argue and Decide)](#5-codex-discussion-routine-argue-and-decide)
  - [6. Git Commands by Phase](#6-git-commands-by-phase)
    - [Create release branch](#create-release-branch)
    - [Create feature branch from release](#create-feature-branch-from-release)
    - [Commit and push feature](#commit-and-push-feature)
  - [7. PR Routine](#7-pr-routine)
  - [8. Release Routine](#8-release-routine)
  - [9. V1 Legacy Download Availability](#9-v1-legacy-download-availability)
  - [10. Quick Checklist](#10-quick-checklist)

## 1. Entry Point
Start from the project index:
- [Documentation/Project/INDEX.md](INDEX.md)

Core workflow reference:
- [Documentation/Project/Planning/REQUIREMENTS_WORKFLOW.md](Planning/REQUIREMENTS_WORKFLOW.md)

## 2. Files You Will Edit
Requirement intake and planning:
- [Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md](Planning/REQUIREMENTS_BACKLOG.md)
- [Documentation/Project/Planning/VERSION_ROADMAP.md](Planning/VERSION_ROADMAP.md)

Traceability:
- [Documentation/Project/Traceability/REQUIREMENTS_TO_TESTS.md](Traceability/REQUIREMENTS_TO_TESTS.md)
- [Documentation/Project/Traceability/REQUIREMENTS_TO_RELEASES.md](Traceability/REQUIREMENTS_TO_RELEASES.md)

Release docs:
- [Documentation/Project/Releases/CHANGELOG.md](Releases/CHANGELOG.md)
- [Documentation/Project/Releases/RELEASE_NOTES_TEMPLATE.md](Releases/RELEASE_NOTES_TEMPLATE.md)
- [Documentation/Project/Releases](Releases)

Governance:
- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)

Regression command source:
- [run_ci_tests.py](../../run_ci_tests.py)

## 3. Step-by-Step Process
### Step A - Add a requirement
1. Open [Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md](Planning/REQUIREMENTS_BACKLOG.md).
2. Add one row in Active Requirements with:
- ID
- Title
- Value
- Acceptance Criteria (binary and testable)
- Priority
- Target Version
- State
- Decision Notes

### Step B - Decide with Codex
1. Start discussion with Codex using the prompts in section 5.
2. Decide: selected now or deferred.
3. Update State and Decision Notes in [Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md](Planning/REQUIREMENTS_BACKLOG.md).

### Step C - Implement on branch
1. Use release branch as integration: release/vX.Y.
2. Create feature branch from release/vX.Y.
3. Implement code and tests.

### Step D - Run regression
Run full suite:
```bash
python run_ci_tests.py
```

### Step E - Update traceability and release docs
1. Update test mapping in [Documentation/Project/Traceability/REQUIREMENTS_TO_TESTS.md](Traceability/REQUIREMENTS_TO_TESTS.md).
2. Update release mapping in [Documentation/Project/Traceability/REQUIREMENTS_TO_RELEASES.md](Traceability/REQUIREMENTS_TO_RELEASES.md).
3. Update [Documentation/Project/Releases/CHANGELOG.md](Releases/CHANGELOG.md).
4. Create or update version release note in [Documentation/Project/Releases](Releases).

### Step F - PR to release branch
1. Open PR to release/vX.Y.
2. Fill [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md).

### Step G - Release close
1. When all selected requirements are done and regression-passed, open PR: release/vX.Y -> main.
2. Tag and publish GitHub release.

## 4. TODO Tag Convention
Use these tags in Decision Notes and optionally commit messages:
- TODO-REQ-<ID>-DISCUSS
- TODO-REQ-<ID>-DECIDE
- TODO-REQ-<ID>-IMPLEMENT
- TODO-REQ-<ID>-TEST
- TODO-REQ-<ID>-DOC
- TODO-REQ-<ID>-PR
- TODO-REQ-<ID>-RELEASE

Example:
- TODO-REQ-120-DISCUSS
- TODO-REQ-120-IMPLEMENT

## 5. Codex Discussion Routine (Argue and Decide)
Use this sequence with Codex for each requirement.

Prompt 1: critical review
```text
Review REQ-120 critically. Give 3 implementation options, pros/cons, risks, and test impact. Recommend one option and explain why.
```

Prompt 2: decision and acceptance criteria
```text
Convert the chosen option for REQ-120 into testable acceptance criteria. Also list what is explicitly out of scope for this version.
```

Prompt 3: implementation
```text
Implement REQ-120 with the smallest safe increment on the current feature branch. Update backlog state, traceability files, and tests. Run full regression and summarize results.
```

Prompt 4: PR readiness
```text
Prepare a PR summary for REQ-120 using the repository PR template. Include changed files, regression evidence, and documentation updates.
```

## 6. Git Commands by Phase
### Create release branch
```bash
git checkout main
git pull
git checkout -b release/v1.2
git push -u origin release/v1.2
```

### Create feature branch from release
```bash
git checkout release/v1.2
git pull
git checkout -b feat/REQ-120-short-slug
```

### Commit and push feature
```bash
git add .
git commit -m "feat(req-120): short description"
git push -u origin feat/REQ-120-short-slug
```

## 7. PR Routine
PR target for feature work:
- feat/fix/docs branch -> release/vX.Y

PR target for release closure:
- release/vX.Y -> main

Use checklist from:
- [.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md)

## 8. Release Routine
1. Freeze release branch.
2. Confirm all selected requirements are Regression Passed in [Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md](Planning/REQUIREMENTS_BACKLOG.md).
3. Finalize [Documentation/Project/Releases/CHANGELOG.md](Releases/CHANGELOG.md).
4. Finalize release note file in [Documentation/Project/Releases](Releases).
5. Merge release/vX.Y -> main.
6. Tag and publish release.

Tag commands:
```bash
git checkout main
git pull
git tag v1.2.0
git push origin v1.2.0
```

## 9. V1 Legacy Download Availability
Keep v1 baseline available on GitHub:
1. Ensure v1 tag exists.
2. Publish GitHub Release for v1.0.0 using:
- [Documentation/Project/Releases/v1.0.0.md](Releases/v1.0.0.md)

## 10. Quick Checklist
- Requirement added in [Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md](Planning/REQUIREMENTS_BACKLOG.md)
- Decision and TODO tags updated
- Implementation done on feature branch from release/vX.Y
- Regression passed with [run_ci_tests.py](../../run_ci_tests.py)
- Traceability updated in [Documentation/Project/Traceability/REQUIREMENTS_TO_TESTS.md](Traceability/REQUIREMENTS_TO_TESTS.md) and [Documentation/Project/Traceability/REQUIREMENTS_TO_RELEASES.md](Traceability/REQUIREMENTS_TO_RELEASES.md)
- Changelog and release notes updated
- PR opened to release branch
- Final PR opened release/vX.Y -> main
