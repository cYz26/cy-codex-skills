# Install and Update

Use this guide when `agent-reach` is missing, outdated, or failing health checks after an upgrade.

## Boundaries

- Keep all persistent Agent Reach data under `~/.agent-reach/`.
- Use `/tmp/` for temporary output.
- Do not clone repos or create setup files inside the user's workspace.
- Do not use `sudo` unless the user explicitly approves.
- If system packages or Docker are missing, explain what needs approval and ask before escalating.

## Fresh Install

Prefer `pipx` on machines where it is available:

```bash
pipx install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
```

If `pipx` is unavailable or Python is externally managed, install in a dedicated virtualenv:

```bash
python3 -m venv ~/.agent-reach-venv
source ~/.agent-reach-venv/bin/activate
pip install https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach install --env=auto
```

Safe mode avoids automatic system-package installation:

```bash
agent-reach install --env=auto --safe
```

Dry run previews changes only:

```bash
agent-reach install --env=auto --dry-run
```

Always verify afterwards:

```bash
agent-reach version
agent-reach doctor
```

## Update

Check whether an update is needed:

```bash
agent-reach check-update
```

If an update is available:

```bash
pip install --upgrade https://github.com/Panniantong/agent-reach/archive/main.zip
agent-reach version
agent-reach doctor
```

Report both the new version and any channel status changes.

## Interpreting `doctor`

- `ok`: usable now
- `warn`: partially configured or backend not responding
- `off` or `error`: missing dependency or failed health check

Use the failing channel names to decide which section of [channel-setup.md](channel-setup.md) to load next.
