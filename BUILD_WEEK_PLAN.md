# OpenAI Build Week 2026 Plan

## Objective

Turn Friday AI from a broad desktop assistant into a focused, demonstrable, and safely controlled desktop engineering agent.

## Phase 1 — Baseline and repository hygiene

- [x] Create isolated `build-week-2026` branch
- [x] Replace placeholder README with a complete project overview
- [x] Add a Build Week roadmap
- [ ] Add `.env.example`
- [ ] Confirm `.gitignore` excludes secrets, local databases, recordings, caches, and build output
- [ ] Document the exact supported Python and Windows versions
- [ ] Establish a reproducible baseline test report

## Phase 2 — OpenAI integration

- [ ] Add a dedicated OpenAI client adapter
- [ ] Keep provider-specific code behind a narrow interface
- [ ] Add startup validation for required configuration
- [ ] Provide clear errors when a key or model is unavailable
- [ ] Avoid logging prompts containing credentials or private data

## Phase 3 — Controlled engineering workflow

- [ ] Approved workspace selection
- [ ] Read-only project inspection
- [ ] Structured plan generation
- [ ] File-impact preview
- [ ] Permission and risk classification
- [ ] Checkpoint before modification
- [ ] Bounded file changes
- [ ] Command allow-list and validation
- [ ] Test and verification execution
- [ ] Diff presentation
- [ ] Rollback after failed verification
- [ ] Cancellation and activity history

## Phase 4 — Reliability

- [ ] Unit tests for path validation
- [ ] Unit tests for command validation
- [ ] Tests for workspace escape attempts
- [ ] Tests for missing permission context
- [ ] Tests for checkpoint and restore
- [ ] Tests for cancellation
- [ ] Smoke test on a clean Windows environment
- [ ] Measure startup and common-action latency

## Phase 5 — Demo and submission

- [ ] Create architecture diagram
- [ ] Capture five clean screenshots
- [ ] Record a two-to-three-minute demonstration
- [ ] Publish a clear GitHub release or tagged commit
- [ ] Write Devpost problem, solution, technical implementation, and challenges sections
- [ ] Disclose pre-existing work and identify Build Week additions
- [ ] Verify every claim in the submission

## Definition of done

The project is submission-ready only when:

1. A new user can install and start it from the README.
2. The demo workflow completes without manual code fixes.
3. Sensitive actions always require the intended approval.
4. The agent cannot edit outside the selected workspace.
5. Verification results and code diffs are visible.
6. No API key, credential, local database, or personal path is committed.
7. The submission clearly separates earlier work from Build Week work.
