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

The legacy `git.push_pr` side-effect ID remains loadable for compatibility, but
new routing must use `git.push` or `github.control_plane_write`.
