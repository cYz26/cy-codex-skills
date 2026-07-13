# Provider Profiles and Migration

DevFlow Core owns workflow routing, OpenSpec artifacts, evidence, review, and
completion gates. Methodology and roadmap providers supply optional capability
implementations; their presence never changes canonical ownership.

## Profiles

| Selection | Use | External dependency |
|---|---|---|
| `core + none` | Default complete workflow without external methodology or roadmap tooling | none |
| `lean-matt + none` | Concise opt-in methodology mapped to selected Matt Pocock skills | pinned Matt source |
| `strict-superpowers + none` | High-discipline opt-in methodology | one selected Superpowers source |
| `<methodology> + gsd` | Add milestone and phase governance to any methodology profile | selected GSD runtime |

Configure `.dev-flow.json` with `workflow.methodology_profile` and
`workflow.roadmap_provider`. Selection resolution is explicit config, then a
matching lock, then unique discovery. Ambiguous or stale sources block the
selected provider; DevFlow never combines provider roots.

`docs/provider_profiles.json` is the capability map. Skills route stable IDs
such as `decision-resolution`, `test-first-execution`, `change-review`, and
`completion-proof`; diagnosis resolves the chosen implementation. This keeps
provider names out of the normal workflow instructions.

## Activation and Source Trust

Diagnosis and activation are capability-scoped. Preview the exact provider
commands and conditional project links before apply:

```bash
python3 scripts/check_dependencies.py --repo <repo> \
  --capability <capability-id> --json
python3 scripts/activate_project_dependencies.py --repo <repo> \
  --capability <capability-id> --dry-run --json
```

Use `--methodology-profile <profile>` and `--roadmap-provider <provider>` to
evaluate a different selection without editing project configuration. Repeat
`--provider-source <provider-id>=<source-id>` to bind portable source records
for that invocation. Diagnostics are always read-only. Activation persists any
of these overrides only when both `--apply` and
`--persist-provider-selection` are present.

Core readiness verifies every required project-local DevFlow skill against the
selected DevFlow plugin root. Lean readiness verifies each triggered Matt route
against the bound `CODEX_HOME` skill hash. Missing or conflicting routes fail
closed; activation reports the repair and never overwrites an ordinary
user-owned skill directory. A syntax-valid configuration with a non-object
`workflow`, selectors, or bindings value, or an unknown profile/provider enum,
is invalid rather than silently defaulting to `core + none`.

Superpowers activation uses only the selected source record's channel-specific
Codex plugin command. Lean Matt activation uses the pinned `v1.1.0` tree and
installs only the six allowed skills; `setup-matt-pocock-skills` is not an
installer and its tracker/spec control plane remains excluded.

GSD's runtime hash alone is insufficient to trust routed instructions. Normal
diagnosis therefore refuses a first lock even when the runtime, local manifest,
skills, and agents agree. An explicit apply must successfully run the exact
pinned installer command from `dependency-provenance.json`; only the
post-install diagnosis receives that in-process receipt and may create an
`authorized-pinned-install` attestation. The lock stores a stable digest of the
relevant manifest file map (excluding its mutable timestamp), skill and agent
hashes, source identity, and installer-command digest. Later diagnosis requires
all of them to match. A malformed manifest, a hand-created first lock, or drift
in either the manifest or installed content fails closed.

## Canonical Artifacts

OpenSpec owns behavior proposal, design, specs, tasks, verification, sync, and
archive. DevFlow owns its control state and evidence below
`.planning/devflow/`. Methodology notes remain drafts until promoted into those
canonical artifacts. Existing `docs/superpowers/specs/` and
`docs/superpowers/plans/` are compatibility inputs, not a second source of
truth.

When GSD is selected, GSD alone owns root `.planning/` roadmap, milestone,
phase, and phase-verification files. DevFlow reads them through the selected
runtime adapter and never writes them. A change-to-phase binding is active only
while both sides exist and the configured provider is selected; archive it
explicitly after OpenSpec and bound phase gates pass.

## Planning Tracking

Diagnostics classify required planning paths as:

- `tracked`: every required path can be committed.
- `partially_tracked`: only some required paths can be committed.
- `local_only`: no required path can be committed.

The latter two are advisory for `core + none` and for GSD with
`commit_docs: false`. Selected GSD with `commit_docs: true` is not roadmap-ready
until its required paths are tracked.

## Migration and Rollback

Run migration diagnosis first. Dry-run reports owners, hashes, action classes,
conflicts, tracking status, and the planned snapshot/rollback path without
writing files. File changes and dependency activation are separate approvals.

```bash
python3 scripts/plugin_project_migration.py --repo <repo> --json
```

Approved apply snapshots every touched file before atomic writes. It moves
legacy DevFlow state into `.planning/devflow/STATE.md`, persists the selected
profile and source lock, and records a hash manifest below
`.planning/devflow/provider-migration/`. It does not delete GSD artifacts,
provider links, or ambiguous user files; a second identical apply is a no-op.

Provider/state apply is deliberately separate from the ordinary
`plugin-project-migration --apply` path:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --apply-provider-files \
  --json
```

The apply result returns the exact canonical manifest at
`.planning/devflow/provider-migration/snapshots/<migration-id>/manifest.json`.

Rollback restores only files whose current hashes still match the apply
manifest. A user edit after migration stops rollback for that path and requires
manual review. Legacy `workflow_version` root state remains read-only until
DevFlow `1.0.0`; GSD markers and mixed schemas are never treated as legacy
DevFlow state.

Rollback is never a default or inferred action. After reviewing the exact
manifest target list, the user must explicitly authorize that file list and
rollback by supplying the manifest:

```bash
python3 scripts/plugin_project_migration.py \
  --repo <repo> \
  --rollback-manifest <absolute-manifest-path> \
  --json
```

`--rollback-manifest` is mutually exclusive with `--apply` and
`--apply-provider-files`. It satisfies the `destructive.cleanup` policy only
for the manifest's exact file list. DevFlow verifies the canonical snapshot
directory, durable checkpoint, target paths, snapshot hashes, and current
post-migration hashes before restoring. Writes are atomic per file and
transactionally compensated back to the verified post-migration state if a
later restore fails. Containment or hash conflicts stop with
`manual_review_required`; DevFlow never guesses or broadens the restore set.
