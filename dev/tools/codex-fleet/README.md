# Codex Fleet

`codex-fleet` aligns the three layers that a Codex plugin update can affect:

1. the configured marketplace snapshot or local source;
2. the installed version cache loaded by Codex;
3. project-local state owned by an explicitly supported stateful plugin.

The command is an independent Python 3.11+ package. A plugin does not need its
own user-facing upgrade CLI. Stateless plugins stop after cache verification;
stateful plugins opt into a closed, tested project Adapter. The first Adapter is
`devflow-v1`, which wraps DevFlow's existing sealed project-refresh CLI.

Inventory also lists the Skills packaged by every enabled Plugin. Those Skills
are not copied or trusted independently: the portable Plugin selector and lock
identify the package, and the full source/cache tree fingerprint covers every
packaged `skills/*/SKILL.md` byte. This makes a Plugin and its Skills one
verifiable release unit.

## Install or run from this repository

Install the standalone package when workstation changes are authorized:

```bash
python3.12 -m pip install ./dev/tools/codex-fleet
codex-fleet --help
```

Repository development and smoke checks can use the wrapper without installing:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.12 dev/scripts/codex_fleet.py --help
```

Neither command above updates a plugin. Installing the package and executing a
fleet apply are separate actions.

## First device: inventory, align, then adopt

Inventory is always read-only and scans no arbitrary project directory. Name
each candidate project explicitly:

```bash
codex-fleet inventory \
  --project game0724=/absolute/path/to/game0724 \
  --json
```

Preview the exact portable manifest/lock, machine-local overlay, and project
marker bytes:

```bash
codex-fleet bootstrap \
  --project game0724=/absolute/path/to/game0724 \
  --manifest ./codex-fleet.json \
  --lock ./codex-fleet.lock.json \
  --device ~/.config/codex-fleet/default.device.json \
  --json
```

After review, adopt only those candidates:

```bash
codex-fleet bootstrap \
  --project game0724=/absolute/path/to/game0724 \
  --manifest ./codex-fleet.json \
  --lock ./codex-fleet.lock.json \
  --device ~/.config/codex-fleet/default.device.json \
  --apply --json
```

Bootstrap never guesses that a local checkout corresponds to a remote. To move
`cy-codex-skills` from a developer-local marketplace to a portable stable Git
source, first review the intended remote/ref and explicitly align the Codex
marketplace registration. `--marketplace-git`, `--marketplace-ref`, and
`--marketplace-channel` validate the desired conversion; a source mismatch
returns `source_alignment_required` instead of rewriting Codex configuration.
Once the runtime registration matches, bootstrap can seal it. A stable channel
cannot use `main`; `main` must be labeled `development`.

## Routine sync and remote upgrade

The safe default is a deterministic dry-run:

```bash
codex-fleet sync \
  --manifest ./codex-fleet.json \
  --lock ./codex-fleet.lock.json \
  --device ~/.config/codex-fleet/default.device.json \
  --json
```

Converge the installed caches and adopted projects to the existing lock without
advancing a Git marketplace:

```bash
codex-fleet sync --apply \
  --manifest ./codex-fleet.json \
  --lock ./codex-fleet.lock.json \
  --device ~/.config/codex-fleet/default.device.json \
  --json
```

On the designated update device, one command advances managed Git snapshots,
refreshes each desired plugin once, verifies source/cache identity, refreshes
eligible projects, and promotes the new lock only after verification:

```bash
codex-fleet sync --apply --advance-lock \
  --manifest ./codex-fleet.json \
  --lock ./codex-fleet.lock.json \
  --device ~/.config/codex-fleet/default.device.json \
  --json
```

Review and share the changed portable lock through your ordinary repository
workflow. Other devices then use locked `codex-fleet sync --apply`.

## Add an additional device

Copy or check out the existing `codex-fleet.json` and
`codex-fleet.lock.json`. Configure the named marketplaces at the manifest's
trusted source/ref, ensure the installed snapshot matches the lock, then run
bootstrap with that device's explicit project paths. Identical portable files
are left unchanged; only the additional device overlay and project adoption
markers are written. No first device absolute path appears in the shared files.

## Project safety and authorization

A project Adapter runs only when all of these agree:

- the portable manifest names the project ID, selector, and known Adapter;
- the device overlay maps that ID to an absolute path with `trusted: true`;
- `.codex-fleet/project.json` has the same ID and managed selectors;
- the selected marketplace source and installed version cache have identical
  verified plugin bytes.

`devflow-v1` selects only actions authorized by `project-refresh-apply`.
`workflow-config-migration`, legacy cleanup, active `AGENTS.md` merge, external
dependencies, and other privileged actions remain named manual work. `--apply`
does not grant those authorities. Project applies and rollbacks hold an
exclusive machine-local lock; plans and verification can run concurrently.

## Verify and roll back

Every applied sync returns a fleet receipt path. Verification rereads the
manifest, lock, marketplace/plugin/cache identity, project markers, and Adapter
receipts. The receipt preserves separate before/after marketplace, plugin, and
cache identities plus explicit Codex-session restart guidance:

```bash
codex-fleet verify --receipt /absolute/path/to/sync-receipt.json --json
```

Rollback is read-only by default:

```bash
codex-fleet rollback --receipt /absolute/path/to/sync-receipt.json --json
```

Apply only receipt-bound reversible actions after reviewing the preview:

```bash
codex-fleet rollback \
  --receipt /absolute/path/to/sync-receipt.json \
  --apply --json
```

Project Adapter effects and a fleet lock preimage are reversible when their
postimages still match. Native marketplace upgrades and installed-cache changes
are intentionally reported as non-reversible because the current Codex CLI has
no receipt-bound version downgrade command. The tool never guesses a global
downgrade. If one project rollback succeeds and a later action fails, the tool
writes a deterministic partial rollback receipt containing completed and
pending action IDs. Automatic retry is then blocked because a non-idempotent
Adapter action may already have run; recover the named pending actions from the
durable receipt instead of replaying the original sync receipt.

After a successful apply/verify, start a new Codex session so the new plugin
cache and skills are loaded.

## Files

- `codex-fleet.json`: portable desired marketplace/plugin/project identities.
- `codex-fleet.lock.json`: portable resolved revisions, versions, and tree
  fingerprints.
- `default.device.json`: machine-local Codex home, local marketplace paths, and
  trusted project paths. Do not share it across devices.
- `.codex-fleet/project.json`: project-local adoption attestation.
- state `receipts/` and `locks/`: durable evidence and machine-local project
  serialization.

Reference JSON Schemas are in `schemas/`; illustrative files are in
`examples/`. Runtime validation is standard-library-only and fails closed on
unknown schemas, duplicates, unknown Adapters, path/marker mismatch, or source
identity drift.

## Exit codes

- `0`: complete success with no outstanding manual item.
- `2`: candidates/preview, verified routine work with named manual actions, or
  rollback preview/incomplete native remediation.
- `3`: invalid input, stale plan, identity/verification failure, lock conflict,
  Adapter failure, or blocked rollback.

Human-readable mode reports the same status and next action. `--json` is the
stable automation interface; every response includes `schemaVersion`, `kind`,
`status`, `ok`, `exitCode`, `actions`, `results`, and `nextAction`.

## Deliberate non-goals

Routine fleet commands do not pull source checkouts, update the Codex
application, install external dependencies, migrate workflow selection, clean
legacy data, overwrite active `AGENTS.md`, publish releases, commit, push,
create a PR, or archive an OpenSpec change.

V1 does not clone or execute arbitrary standalone Skill repositories. A remote
Skill collection should be published through a managed Codex Plugin marketplace
so the same snapshot, cache, lock, and integrity gates apply. A future dedicated
Skill-source Adapter would need its own fixed protocol and tests; the manifest
cannot provide a shell command.
