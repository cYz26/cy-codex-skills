# Roadmap: Context Fixer

## Overview

Context Fixer is already implemented as a local Python CLI. The immediate
roadmap is to make its Codex-first workflow state reliable, record the current
system baseline, then use OpenSpec/GSD gates for future behavior changes.

## Phases

- [x] **Phase 1: Foundation** - Initialize workflow, confirm current-system
  scope, and record repeatable verification evidence.

## Phase Details

### Phase 1: Foundation
**Goal**: Make the Context Fixer project ready for safe, spec-driven brownfield
development.
**Depends on**: Nothing (first phase)
**Requirements**: current-system
**Success Criteria** (what must be TRUE):
  1. Project workflow state is readable by the local orchestrator and GSD tools.
  2. OpenSpec `current-system` describes concrete baseline behavior.
  3. Repeatable verification commands are recorded with fresh evidence.
  4. Archive remains blocked until the user approves the baseline and gates are
     satisfied.
**Plans**: 1 plan

Plans:
- [x] 01-01: Complete current-system baseline and verification record.

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 1/1 | Complete | 2026-05-18 |
