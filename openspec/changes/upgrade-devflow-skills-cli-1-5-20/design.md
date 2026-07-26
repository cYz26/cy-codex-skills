## Context

DevFlow records the executable used to install its six approved Matt skills in
`docs/dependency-provenance.json`. The development and release copies currently
pin `skills@1.5.9`. On 2026-07-23, `npm view skills version engines dist-tags
--json` reported `1.5.20` as `latest` with Node `>=22.20.0`; the package points
to `vercel-labs/skills`. Running `npx -y skills@1.5.20 --help` confirmed that
the existing `add`, `--skill`, `--agent`, and `--yes` invocation remains valid.
The workstation's Node `v24.13.0` satisfies the new requirement.

The local scan found only two stale pins: the development provenance and its
generated release counterpart. The installer pin is provenance metadata, not
the source identity of the vendored Matt skills, so `mattpocock/skills`
`v1.1.0`, its commit, licenses, adaptations, and hashes remain unchanged.

## Skill Routing Ledger

- artifact-status: final
- kind: external CLI dependency contract update
- workflow mode: Full OpenSpec
- capability-research: required and used; npm metadata, package repository,
  CLI help, local Node, provenance files, tests, and release mapping inspected
- decision-resolution: required and used; exact released pin and unchanged
  install argument contract selected with no unresolved choices
- decision-grilling: skipped; authoritative evidence and the user's explicit
  `1.5.20` update request leave no Open Question
- implementation-planning: required and used through `ai-native-tech-plan`
  and `change-plan`
- architecture-guidance: skipped; no module boundary or architecture changes
- domain-language-modeling: skipped; no domain concepts or invariants change
- openspec-routing: required and used through
  `upgrade-devflow-skills-cli-1-5-20`
- test-first-execution: required for the provenance contract change
- delegation: skipped; the write set is small, shared, and not independently
  parallelizable

## Goals / Non-Goals

**Goals:**

- Pin the public Matt skill installation command to `skills@1.5.20`.
- Record the installer's Node `>=22.20.0` runtime requirement.
- Prove development and packaged provenance expose the same exact command and
  leave the Matt source contract unchanged.
- Synchronize and evaluate the release package only after the separate release
  authorization gate is satisfied.

**Non-Goals:**

- Updating `mattpocock/skills` beyond `v1.1.0` or changing vendored bytes.
- Installing or executing the Matt skill installation command against a real
  project.
- Refreshing the internal plugin cache or any project-local skill links.
- Changing OpenSpec, Plugin Eval, another plugin, or another dependency.
- Committing, pushing, creating a PR, archiving, or cleaning legacy files.

## Decisions

### 1. Pin `1.5.20` instead of resolving `latest` at install time

The provenance command SHALL use `skills@1.5.20`. A fixed executable version
keeps activation reproducible while the recorded verification date makes
future registry drift visible.

Rejected alternative: `skills@latest`, because a later publish could change
CLI behavior without a reviewed DevFlow change.

### 2. Record installer runtime requirements beside the install command

The methodology provenance SHALL add
`"runtimeRequirements": {"node": ">=22.20.0"}`. This metadata belongs to the
installer executable and is separate from the OpenSpec dependency's Node
requirement.

Rejected alternative: relying on the workstation's current Node version,
because packaged provenance must remain understandable on another machine.

### 3. Lock the whole public command contract in tests

Development and packaged tests SHALL assert the exact executable pin, the Node
requirement, and the existing repository, skill, agent, and confirmation
arguments. This catches both stale versions and accidental installer behavior
changes.

Rejected alternative: a substring-only assertion, because it would not prove
the public command remains deterministic.

### 4. Preserve the release authorization boundary

Development source and tests can be implemented under this approved change.
The generated `plugins/dev-flow` counterpart SHALL be updated only through the
release promotion gate after fresh source verification and explicit durable
release authorization. Plugin Eval runs against that release target.

## Completion Contract

- Development provenance names `skills@1.5.20`, Node `>=22.20.0`, and the
  unchanged Matt source/install arguments.
- Focused tests show a failing old-pin expectation before implementation and
  pass after the source update.
- Strict change validation, workflow validation, source test coverage, and
  diff checks pass.
- After separately authorized promotion, release provenance is byte-equivalent
  to source, packaged/runtime checks pass, and release Plugin Eval has zero
  failures or an approved documented warning disposition.
- The installed internal cache remains untouched and is reported as stale if
  the final dry-run detects source drift.

## Critical Path

1. Add exact development and packaged provenance assertions and record RED.
2. Update only the development provenance contract and record GREEN.
3. Complete source and OpenSpec verification.
4. Stop at `READY_FOR_EXTERNAL_EFFECT` unless release promotion is explicitly
   authorized.
5. If authorized, promote, run packaged/runtime checks and Plugin Eval, then
   record final evidence.

## Incidental Finding Budget

At most one bounded RED/GREEN guard may be added inside the provenance tests.
Any unrelated dependency, cache, migration, or release finding is
`DEFER_AND_CONTINUE` unless it blocks the Completion Contract; material scope
or authorization expansion is `BLOCKED_AWAITING_HUMAN`.

## Escalation Triggers

- The `1.5.20` CLI lacks any existing install argument.
- The package source or registry metadata conflicts with npm output.
- Updating the pin requires changing Matt source bytes, hashes, public
  activation behavior, or another dependency.
- Release promotion, cache refresh, installation, migration, archive, commit,
  push, PR, cleanup, or another external effect lacks explicit authorization.

## Capability Slices

1. **Contract and RED**: add exact source/release test expectations and capture
   the old-pin failures.
2. **Development source GREEN**: update the source provenance date, installer
   pin, and runtime requirement without touching Matt content.
3. **Source verification**: run focused, complete source, strict OpenSpec,
   workflow, and diff checks; record the release-ready receipt.
4. **Authorized release verification**: promote the generated counterpart,
   run full and packaged checks plus Plugin Eval, and verify idempotence.

## Execution Ledger

| Slice | Owner | Write Set | Evidence | Human Gate | Status |
|---|---|---|---|---|---|
| Contract and RED | main agent | two DevFlow test files | expected focused failures | none | pending |
| Development source GREEN | main agent | development provenance | focused passing tests | none | pending |
| Source verification | main agent | change evidence, tasks, workflow state | source suite and validators | none | pending |
| Release verification | main agent | generated `plugins/dev-flow/**` counterpart and evidence | promotion, packaged tests, runtime, Plugin Eval | explicit release authorization | blocked |

## Continuation Policy

Execution is `auto-until-terminal`. The main agent continues through RED,
GREEN, and source verification without routine confirmation. It returns
`READY_FOR_EXTERNAL_EFFECT` at the release gate unless explicit release
authorization already exists. Archive, cache refresh, install, commit, push,
and PR remain out of scope.

## Validation Commands

```bash
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_dependencies.py'
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests -p 'test_packaged_runtime.py'
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/run_devflow_prepromotion_tests.py
openspec validate upgrade-devflow-skills-cli-1-5-20 --strict
python3.12 dev/plugins/dev-flow/scripts/validate_workflow_state.py --repo . --json
git diff --check
python3.12 dev/plugins/dev-flow/scripts/sync_release_assets.py --target dev-flow --json
python3.12 dev/plugins/dev-flow/scripts/release_promotion_gate.py --target dev-flow --apply --json
python3.12 -m unittest discover -s dev/plugins/dev-flow/tests
python3.12 -m unittest discover -s plugins/dev-flow/tests
python3.12 plugins/dev-flow/scripts/verify_release_runtime.py --plugin-root plugins/dev-flow --json
plugin-eval analyze plugins/dev-flow --format markdown
python3 dev/scripts/codex_auto_update_plugins_skills.py --json
```

## Risks / Trade-offs

- [Node requirement is recorded but not enforced for this auxiliary installer]
  -> Tests make the contract visible; real installation remains an explicit,
  separately diagnosed action.
- [Package `latest` changes after this verification] -> The exact pin remains
  reproducible and a future updater dry-run reports new drift.
- [Release counterpart remains stale before authorization] -> Source
  verification reports the expected drift and does not claim packaged
  completion.

## Migration Plan

1. Update and verify the development contract.
2. Record a source-bound release verification receipt.
3. After explicit release authorization, promote only `dev-flow`.
4. Verify the generated release and leave installed caches untouched.

Rollback is a source/release revert to `skills@1.5.9` with removal of the
methodology installer runtime metadata. No project or user installation state
requires rollback.

## Open Questions

None.
