# Roadmap-bound Archive

Read this file only when an active DevFlow roadmap binding exists and
`roadmap-lifecycle` is selected.

For a GSD binding, run `gsd-verify-work`, then ingest the canonical UAT
artifact:

```bash
python3 dev/plugins/dev-flow/scripts/record_verification.py \
  --repo <repo> --gsd-change <change> --gsd-phase <phase> --json
```

The command resolves
`.planning/phases/<phase-dir>/<phase-num>-UAT.md` through the pinned read-only
GSD adapter, verifies complete/pass/no-gap state, and records its hash. Command
text or caller-authored result claims are not UAT evidence.

Only after OpenSpec is verified and actually archived, preview the binding
transition and then apply it with separate authorization:

```bash
python3 dev/plugins/dev-flow/scripts/archive_roadmap_binding.py \
  --repo <repo> --change <change> --json
python3 dev/plugins/dev-flow/scripts/archive_roadmap_binding.py \
  --repo <repo> --change <change> --apply \
  --authorize-archive-binding --json
```

Preview is always read-only. Apply requires canonical-write and archive
authorization and re-checks the OpenSpec archive, DevFlow state, and current
UAT hash before atomically updating `.dev-flow.json`.
