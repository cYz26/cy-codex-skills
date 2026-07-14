## Target State

DevFlow retains sixteen focused public skills, removes six duplicated orphan
resources, directly links every retained/new support file, and moves
branch-specific detail out of the highest-cost main skill bodies without
changing names, routing, invocation policy, scripts, or safety gates.

## Completion Contract

- Exact skill-set and supporting-resource reachability tests pass.
- Release invoke cost is at most 10,000 Plugin Eval tokens with zero failures
  and score no lower than 86/B.
- Development, packaged, runtime, strict OpenSpec, release parity, workflow,
  and diff checks pass with evidence recorded.
- No installed cache, project migration, archive, commit, or push occurs.

## 1. Evidence Baseline and RED Contracts

- [x] 1.1 Audit all sixteen skills across routing, references, packaging,
  compatibility, project links, and OpenSpec history under the validated Agent
  Task Contract.
- [x] 1.2 Resolve the release-preferred Plugin Eval target and capture the
  86/B, zero-failure, 385 trigger, 11,996 invoke, 27,397 deferred, and 12,381
  active-token baseline plus the improvement brief.
- [x] 1.3 Confirm official Codex progressive-disclosure and
  `allow_implicit_invocation` semantics, and record why invocation-policy
  changes and public-name deletion are blocked by missing usage/migration
  evidence.
- [x] 1.4 Add exact-set regression coverage for source skill directories,
  `PROJECT_ORCHESTRATOR_SKILLS`, and project-migration `projectLocalSkills`.
- [x] 1.5 Add regression coverage requiring every `assets/` and `references/`
  file to be named by its owning `SKILL.md`, plus absence checks for the six
  approved dead resources.
- [x] 1.6 Run the focused tests before implementation and record the expected
  RED failures for unlinked resources, missing conditional references, and the
  still-present dead-resource set.

## 2. Progressive-Disclosure Skill Optimization

- [x] 2.1 Thin `dev-flow-refresh` into a global-first/project-second
  orchestration facade and move project refresh/AGENTS reporting plus provider
  cleanup commands into directly linked one-level references.
- [x] 2.2 Keep `context-health-check` detection and decision semantics active,
  moving goal/delegation disposition and historical-session recovery detail
  into directly linked conditional references.
- [x] 2.3 Keep ordinary `plugin-project-migration` sync/apply gates active,
  moving provider-file migration and destructive rollback detail into a
  directly linked conditional reference.
- [x] 2.4 Keep `verify-and-archive` verification/archive gates active, moving
  selected-roadmap binding commands into a directly linked conditional
  reference.
- [x] 2.5 Link `ai-native-tech-plan` directly to its retained
  `task-ledger-template.md` and `goal-prompt-template.md` resources with
  explicit read/use conditions.
- [x] 2.6 Remove the three duplicated unlinked `ai-native-tech-plan` resources
  and all three unlinked `checkpoint-compact` references from the source tree.
- [x] 2.7 Clarify the `dev-flow-refresh` versus `project-setup` trigger boundary
  without changing natural-language invocation policy or public skill names.
- [x] 2.8 Run focused GREEN tests and all sixteen source-skill quick validators.

## 3. Static Budget Iteration and Broad Source Verification

- [x] 3.1 Re-run Plugin Eval on the development plugin and release-preferred
  target after source optimization; if invoke cost exceeds 10,000, remove
  additional duplicated prose while preserving required active gates.
- [x] 3.2 Verify all sixteen skills remain 100/A individually or record and fix
  every regression before continuing.
- [x] 3.3 Run focused skill, routing, dependency, migration, provider-guidance,
  and release-smoke tests.
- [x] 3.4 Run complete development unittest discovery and require zero failures
  or skips not already accepted by the repository baseline.
- [x] 3.5 Run strict validation for
  `optimize-devflow-skill-portfolio`, all active OpenSpec changes, workflow
  state, and `git diff --check`.

## 4. Generated Release and Runtime Verification

- [x] 4.1 Resolve and record the release counterpart with
  `sync_release_assets.py --eval-target` before evaluating or promoting.
- [x] 4.2 Run the release promotion dry-run, apply the approved `dev-flow`
  generated-asset update, then require the second dry-run to report `current`.
- [x] 4.3 Run packaged unittest discovery and runtime archive verification,
  including managed-output, wrapper, manifest, and checksum checks.
- [x] 4.4 Run final release-target Plugin Eval and record score, grade, risk,
  failures, warnings, trigger/invoke/deferred/explicit-only/total budgets, and
  the no-observed-usage limitation.

## 5. Review, Evidence, and Closeout

- [x] 5.1 Dispatch independent read-only reviews for skill correctness,
  compatibility, direct-reference integrity, tests, and release readiness; fix
  every actionable P0/P1/P2 finding.
- [x] 5.2 Record changed files, RED/GREEN logs, validation commands, Plugin Eval
  comparison, remaining warnings, rollback, and stale invocation-policy
  supersession in change evidence.
- [x] 5.3 Update the root `TASK_LEDGER.md` and `.planning/devflow/STATE.md` only
  after fresh verification, leaving archive disallowed and naming the next
  explicit action.
- [x] 5.4 Run the local-reference updater dry-run and report release sync,
  installed-cache refresh need, and project-local migration status without
  applying cache or project changes.
- [x] 5.5 Run final `git status --short`, `git diff --stat`, and
  `git diff --check`; do not archive, commit, or push.

## Capability Slices

| Slice | Scope | Validation | Cleanup | Status |
|---|---|---|---|---|
| S1 | Audit, official evidence, baseline, RED invariants | Focused RED tests and baseline report | No mutations outside planning | done |
| S2 | Main-body thinning, direct references, dead-resource removal | Focused GREEN plus 16 quick validators | Remove six approved resources only | done |
| S3 | Budget iteration and source verification | Dev Plugin Eval, focused/full tests, strict OpenSpec | Eliminate duplicated prose found by eval | done |
| S4 | Generated release and runtime | Promotion current, packaged tests, runtime verifier, release Eval | No stale generated outputs | done |
| S5 | Independent review and durable evidence | Review dispositions, state/ledger, diff checks | No cache/migration/archive side effect | done |

## Execution Ledger

| Item | Owner | Write Set | Required Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| DF-SP-1 | main + read-only audit agents | OpenSpec and audit contract | 16-skill matrix, official docs, baseline Eval | Stop on unresolved public consumer | done |
| DF-SP-2 | main | source skills and focused tests | RED/GREEN, quick validation | Six-file deletion set only | done |
| DF-SP-3 | main | source skills/tests/evidence | <=10,000 invoke and full source checks | No invocation-policy change | done |
| DF-SP-4 | main | generated `plugins/dev-flow/**` | promotion/current, package/runtime/Eval | Repository generation only | done |
| DF-SP-5 | main + read-only reviewers | evidence, ledger, state | findings disposition and final diff | No archive/commit/push/cache refresh | done |

## Validation Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest \
  dev/plugins/dev-flow/tests/test_project_orchestrator.py \
  dev/plugins/dev-flow/tests/test_release_smoke.py -v
python3.12 /Users/cY/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  dev/plugins/dev-flow/skills/<skill>
node /Users/cY/.codex/plugins/cache/openai-curated-remote/plugin-eval/0.1.2/scripts/plugin-eval.js \
  analyze plugins/dev-flow --format json
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover \
  -s dev/plugins/dev-flow/tests -v
openspec validate optimize-devflow-skill-portfolio --strict
openspec validate --all --strict
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --json
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py \
  --repo . --apply --json
PYTHONDONTWRITEBYTECODE=1 python3.12 -m unittest discover \
  -s plugins/dev-flow/tests -v
python3.12 plugins/dev-flow/scripts/verify_release_runtime.py \
  --plugin-root plugins/dev-flow --json
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py \
  --repo . --json
python3.12 dev/scripts/codex_auto_update_plugins_skills.py \
  --repo . --codex-home /Users/cY/.codex \
  --skip-codex-update --skip-openai-curated-cache \
  --skip-external-updaters --json
git diff --check
```

## Risks / Rollback

- Stop before any public skill deletion, invocation-policy change, dependency,
  migration, cache mutation, or unresolved compatibility expansion.
- If a moved rule becomes unreachable or a focused test regresses, restore it
  to the owning main body before continuing.
- Repository changes are reversible with a normal Git revert; no user-global or
  project migration rollback is needed because those writes remain forbidden.

## Review Checklist

- [x] Target State and Completion Contract remain complete and non-prototype.
- [x] Every retained resource is directly reachable and non-duplicative.
- [x] All public names, capability routes, hooks, wrappers, and manifests remain
  coherent.
- [x] Static budget improvement does not rely on disabling implicit routing.
- [x] Full source, generated release, runtime, OpenSpec, workflow, and Plugin
  Eval evidence is fresh.
- [x] Archive, commit, push, cache refresh, and project migration remain
  unperformed.
