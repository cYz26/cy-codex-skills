## Context

DevFlow publishes sixteen project-local skills. All sixteen exist in the source
and release trees, the project-migration manifests, the dependency catalog, the
required project-skill checks, activation installs, packaged smoke tests, and
this repository's `.agents/skills` links. The current migration implementation
does not compare a prior managed skill set with a new smaller set, so deleting a
skill name would strand old links and turn a cleanup into an unmanaged
compatibility break.

Release-target Plugin Eval 0.1.2 reports 86/B, medium risk, zero failures, and
three aggregate budget warnings:

- trigger cost: 385 tokens;
- invoke cost: 11,996 tokens;
- deferred cost: 27,397 tokens;
- active budget: 12,381 tokens.

Every skill evaluated independently at 100/A with zero failures or warnings.
The useful optimization signal is therefore portfolio structure, not deletion
of a low-scoring skill. `dev-flow-refresh` is the largest active body at 199
lines and 1,880 invoke tokens, followed by `context-health-check` and
`plugin-project-migration`. Eight existing supporting files are not linked from
their owning `SKILL.md`; five have no current consumer beyond historical
artifacts, while the task-ledger and goal-prompt templates remain live test and
output resources.

Official OpenAI skill documentation confirms that Codex first exposes skill
metadata, loads `SKILL.md` only after selection, and reads supporting references
as needed. It also confirms that `allow_implicit_invocation: false` prevents
natural-language implicit selection and leaves explicit `$skill` invocation as
the supported entry. Because DevFlow has no observed-usage corpus, invocation
policy is not a safe surrogate for content optimization.

### Skill Routing Ledger

- kind: compatibility-changing plugin refactor and cleanup
- workflow mode: Full OpenSpec
- artifact-status: final; Open Questions are resolved
- capability-research: required/used; official Codex skill semantics, local
  source/release/cache scans, Plugin Eval, manifests, tests, and Git history
- decision-resolution: required/used; `feature-intake` classified the work and
  evidence resolved the deletion and invocation-policy boundaries
- decision-grilling: skipped; no unresolved choice remains after the three
  independent audits
- implementation-planning: required/used; `change-plan` and
  `ai-native-tech-plan` structure this OpenSpec change
- architecture-guidance: required/used; `capability-research` plus
  `ai-native-tech-plan`
- OpenSpec routing: required/used; new change
  `optimize-devflow-skill-portfolio`
- roadmap routing: skipped; `.dev-flow.json` explicitly selects
  `roadmap_provider: none`
- methodology profile: `core`; no unselected provider contributes gates
- Open Questions: none

### Capability Evidence

- `authoritative_current`: OpenAI `Build skills` documentation fetched on
  2026-07-13; progressive disclosure and invocation-policy semantics confirmed.
- `local_scan`: all sixteen source/release/project skills, dependency catalog,
  project-migration manifests, activation and migration code, focused and
  packaged tests, current installed-cache parity, OpenSpec history, and release
  Plugin Eval.
- `comparison`: deleting or consolidating public names needs a retirement
  migration and usage evidence; toggling invocation policy reduces static cost
  by disabling natural-language discovery; compact bodies plus conditional
  references preserve behavior and address the measured active cost.
- `assumptions`: external repositories and real invocation telemetry remain
  unobserved. That uncertainty blocks public-name deletion but does not block
  removal of duplicated files with no live link or unique contract.
- `contract`: exact-set, direct-link, focused behavior, source/release parity,
  full test, runtime, strict OpenSpec, and release-target Plugin Eval commands
  are recorded in `tasks.md`.

## Target State

DevFlow keeps sixteen focused, naturally discoverable public skills. Umbrella
skills explain ownership and selection in a compact main body, while detailed
commands for conditional branches live in directly linked one-level references.
No supporting file is orphaned, no canonical rule is duplicated solely for
historical convenience, source and release packages match, and the release
plugin retains zero Plugin Eval failures with a lower active invoke budget.

## Goals / Non-Goals

**Goals:**

- Make each public skill's job and downstream owner distinct.
- Reduce aggregate active invoke cost below 10,000 Plugin Eval tokens.
- Keep all supporting files directly discoverable from their owning skill.
- Delete only duplicated, unlinked resources with no unique live contract.
- Preserve all public names, routing, safety gates, commands, and provider
  selection behavior.
- Record a durable supersession of the stale explicit-only planning decision.

**Non-Goals:**

- No public skill retirement, alias, extraction to a new plugin, or project-link
  retirement migration.
- No invocation-policy change, live/paid benchmark, or claim about actual user
  usage.
- No script behavior, public CLI, provider, dependency, hook, persistence, or
  schema change.
- No installed-cache refresh, project migration, archive, commit, or push.

## Decisions

### 1. Retain the complete public portfolio

The portfolio remains:

| Ownership | Skills |
|---|---|
| Intake and routing | `project-orchestrator`, `feature-intake`, `capability-research` |
| Planning and execution | `change-plan`, `ai-native-tech-plan`, `execute-task`, `verify-and-archive` |
| Project and context lifecycle | `project-setup`, `workflow-doctor`, `checkpoint-compact`, `context-health-check` |
| Maintenance | `codex-updater`, `dev-flow-refresh`, `plugin-project-migration`, `context-tool-audit` |
| Optional external adapter | `claude-code-delegate` |

The maintenance skills remain separate because updater inventory, DevFlow-wide
refresh ordering, project migration, and context cleanup have different apply
and rollback gates. `dev-flow-refresh` becomes a thinner orchestration facade
over these owners rather than duplicating their full procedures.

Alternatives rejected:

- Delete `claude-code-delegate`: it is the strongest future extraction candidate
  but is still packaged, required, explicitly invokable, and owns a release
  wrapper. It is already explicit-only, so deletion saves no implicit budget.
- Merge updater, refresh, migration, and doctor: this would blur distinct side
  effects and contradict the existing migration and refresh contracts.
- Delete names with few direct references: every name is in the managed public
  set, and reference count is not usage evidence.

Any future public retirement requires a separate change with a versioned retired
skill set, trusted-link dry-run/apply/rollback, alias window, custom-path
preservation, and idempotent project-state migration.

### 2. Apply progressive disclosure only to conditional detail

The following skills keep selection, safety, and completion rules in
`SKILL.md`, while conditional procedures move to direct references:

- `dev-flow-refresh`: project refresh/AGENTS reporting and provider cleanup;
- `context-health-check`: goal/delegation disposition and historical recovery;
- `plugin-project-migration`: provider-file migration and destructive rollback;
- `verify-and-archive`: selected-roadmap archive binding.

`ai-native-tech-plan` keeps its live task-ledger and goal-prompt resources and
links to both from the main body. Each reference is one level deep, is named in
`SKILL.md`, and includes only detail not duplicated in the main procedure.

Alternative rejected: move all safety rules out of `SKILL.md`. Authorization,
stop conditions, and output requirements must remain active whenever the skill
is selected.

### 3. Remove the evidence-backed dead resource set

Delete these duplicated, unlinked files from source and generated release:

- `ai-native-tech-plan/assets/review-checklist.md`;
- `ai-native-tech-plan/references/agents-md-snippet.md`;
- `ai-native-tech-plan/references/planning-principles.md`;
- `checkpoint-compact/references/boundary-rules.md`;
- `checkpoint-compact/references/compact-policy.md`;
- `checkpoint-compact/references/recovery-playbook.md`.

The first three repeat the skill body, root templates, or durable AGENTS rules.
The checkpoint references have zero inbound links and duplicate the concise
checkpoint procedure. Keep `task-ledger-template.md` and
`goal-prompt-template.md`; they remain output resources with live tests and are
made directly discoverable.

### 4. Preserve natural-language invocation

The current policy remains fifteen implicit skills plus explicit-only
`claude-code-delegate`. The completed but unarchived
`optimize-devflow-plugin-eval-followup` change still describes nine skills as
explicit-only; later provider-architecture work and current release tests
superseded that decision. This change records the current policy as deliberate
and does not sync or archive the stale delta. Archival reconciliation remains a
separate authorization boundary.

Alternative rejected: restore the old explicit-only split to improve a static
score. Official semantics make that a routing behavior change, and no observed
usage or outcome corpus justifies it.

### 5. Enforce portfolio invariants with tests

Focused tests assert:

- the exact sixteen-name set is identical across source skill directories, the
  dependency catalog, and the project-migration manifest;
- every file below a skill's `assets/` or `references/` directory is named by
  that skill's `SKILL.md`;
- removed resource paths stay absent and retained/new references exist;
- existing invocation-policy and routed-skill tests remain green.

Release promotion supplies source/release parity and packaged/runtime evidence;
the implementation does not hand-edit the generated release tree.

### 6. Use release-target evaluation as the quantitative gate

The primary acceptance target is the release-preferred `plugins/dev-flow`
package resolved by `sync_release_assets.py --eval-target`. Development-path
evaluation remains diagnostic. Completion requires zero failures, score at
least 86/B, invoke cost at most 10,000 tokens, and recorded before/after
findings. Deferred cost may remain heavy because release scripts/templates are
outside this skill-body cleanup, but removed dead resources must not increase it.

## Completion Contract

- All sixteen skills have a distinct retained owner and no public name is
  deleted.
- The six approved dead resources are absent and every remaining/new support
  file is directly linked from `SKILL.md`.
- Focused RED tests fail before implementation and pass after it.
- Development and packaged test suites, strict OpenSpec validation, release
  promotion/current checks, runtime verification, workflow validation, and
  `git diff --check` pass.
- Release-target Plugin Eval has zero failures, at least 86/B, and invoke cost
  no greater than 10,000 tokens.
- Exact commands, changed files, risks, and the no-observed-usage limitation are
  recorded in the change evidence and DevFlow state.

## SubAgent Strategy

The read-only audit used the validated contract at
`.planning/agent-tasks/20260713-devflow-skill-portfolio-audit.md` with disjoint
reference, evaluation, and compatibility scopes. Implementation remains
serialized through the main agent because skill bodies, shared tests, release
generation, and OpenSpec evidence overlap. Independent agents may review the
final diff read-only; the main agent owns all canonical and generated writes.

## Risks / Trade-offs

- [Risk] A reference removes a safety rule from the active body → keep
  authorization, stop, and verification boundaries in `SKILL.md`; move only
  branch-specific command detail and cover it with focused tests.
- [Risk] Static budget improves while real outcomes regress → preserve
  descriptions, names, invocation policy, and behavioral tests; record missing
  observed usage as residual risk rather than claiming runtime savings.
- [Risk] Generated release drift hides a source deletion → use the release
  promotion gate, post-sync current check, runtime verifier, and exact-set test.
- [Risk] The stale explicit-only OpenSpec delta is mistaken for current policy
  → state the supersession here and in verification; do not archive or sync it
  without a separate reconciliation decision.
- [Trade-off] Supporting references may leave deferred budget heavy → active
  invoke cost and correctness take precedence; remove only genuinely dead
  deferred material.

## Migration Plan

No user/project migration is required because public names, manifests, and
invocation policy remain stable. Implement source changes with TDD, promote the
generated release through the authorized repository gate, and verify parity.
Rollback is a normal Git revert of this change before external refresh; no
cache, project link, provider state, or user configuration is mutated.

## Open Questions

None. Public-skill extraction and observed-usage benchmarking are explicitly
outside this change and require separate evidence and authorization.
