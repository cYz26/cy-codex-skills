---
name: kb-enable-project
description: Use when a repository should be configured for AgentKB project problem capture.
---

# KB Enable Project

Use when a user wants a project to collect AgentKB context, hook problem
signals, and manual problem reflection drafts.

AgentKB keeps Markdown as the canonical storage format. Load the smallest
sufficient context first, and make every write reviewable with Git diff.

## Procedure

1. Check status:

```bash
python3 scripts/kb_project.py status --repo <repo> --json
```

2. If unconfigured, enable the project:

```bash
python3 scripts/kb_project.py enable \
  --repo <repo> \
  --vault <vault> \
  --project <project> \
  --owner <owner> \
  --json
```

3. Verify the configured project:

```bash
python3 scripts/kb_project.py verify --repo <repo> --json
```

4. After failures, use automatic problem signals from `_agent/problem-signals/`
   as evidence for `kb-reflect`.
5. For issues discovered outside hooks, record a manual draft:

```bash
python3 scripts/kb_problem.py record \
  --repo <repo> \
  --incident "<what happened>" \
  --evidence "<how it was observed>" \
  --json
```

## Safety

Hooks collect sanitized problem signals only. They must not directly rewrite
canonical notes, accepted decisions, playbooks, or skills. Review problem
signals and manual drafts with `kb-reflect`; promote repeated stable lessons
with `kb-promote`.
