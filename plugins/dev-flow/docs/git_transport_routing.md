# Git Transport vs GitHub Control Plane

DevFlow treats repository transport and GitHub platform writes as independent
capabilities:

| Operation | Tool path | Side effect | Credential signal |
| --- | --- | --- | --- |
| commit | native `git` | `git.commit` | local Git identity |
| push or tag push | native `git` and configured remote | `git.push` | Git remote transport |
| pull request, GitHub release, repository settings | GitHub control plane | `github.control_plane_write` | usable GitHub platform credentials |

A gh authentication failure is not Git transport failure. Do not run `gh auth
login` for a Git-only operation. Once push is explicitly authorized, inspect
the configured remote and run the read-only native probe:

```bash
python3 scripts/git_transport_preflight.py --repo <repo> \
  --remote origin --branch <branch> --json
```

`GIT_TRANSPORT_READY` means the selected remote accepted `git ls-remote`; it
does not authorize or perform a push and does not guarantee branch-protection
or fast-forward acceptance. `GIT_TRANSPORT_BLOCKED` means the native Git path
needs repair. Never substitute `gh auth status` for this probe.

For `github.control_plane_write`, allow one diagnosis and at most one
applicable remediation attempt. If credentials remain unavailable, stop that
platform path and report its exact gate. Do not repeat the authentication loop,
and do not block an independently authorized native Git operation.

## Deterministic Release Publication

For a deterministic release bound to an immutable tag, select the control-plane
execution path in this order:

1. `github_actions`
2. `github_cli`
3. `human_web`

The `github_actions` path is eligible only when the reviewed release workflow
exists in the immutable tag target, repository policy permits it, and the
workflow uses `GITHUB_TOKEN` with explicit least privilege permissions. Before
the separately authorized tag push, verify the expected tag target, reviewed
release inputs, workflow identity, and the absence of a conflicting tag or
Release. A workflow that exists only on another branch does not satisfy this
gate.

Tag transport and Release publication remain separate effects. Pushing the tag
requires `git.push`; publishing the Release requires
`github.control_plane_write`. The Actions path does not require local `gh`
authentication. If Actions is ineligible before the tag push, use an already
authenticated `github_cli` path or stop at a named-human `human_web` gate after
the bounded GitHub CLI recovery budget is exhausted. Do not apply this
Actions-first policy to pull requests or repository settings.

A successful tag push or workflow dispatch is not publication proof. Require
publication readback of the expected tag, target, published state, draft state,
and prerelease state. If an authenticated read path is unavailable for a
private repository, record named-human confirmation of the successful workflow
and published Release. Keep local promotion blocked until that readback is
recorded.

If the tag exists remotely but Actions fails or publication readback cannot be
completed, preserve the tag. Do not delete or retarget it automatically; stop
local promotion and recover against the same reviewed tag identity.

The legacy `git.push_pr` side-effect ID remains loadable for compatibility, but
new routing must use `git.push` or `github.control_plane_write`.
