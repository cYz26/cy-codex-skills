---
name: context-fixer
description: Use when auditing Codex context usage, context pressure, compaction timing, request trace attribution, or AI project configuration for a local repository.
---

# Context Fixer

Context Fixer is a local-first auditor for Codex sessions, context usage,
compaction timing, request traces, and AI project configuration.

Use this skill when the user asks to:

- check why a Codex project or session is using too much context;
- inspect compaction timing or checkpoint readiness;
- audit global/project Codex skills, plugins, MCP servers, or instruction files;
- generate a sanitized context report for the current repository;
- analyze an explicit request trace JSONL file.

## Privacy

The report is designed to stay sanitized. Do not print prompt bodies, chat
contents, tool argument bodies, or tool output bodies. If the user provides a
trace, treat it as potentially sensitive and prefer local file paths.

## Tool Root

The development checkout for this tool is:

```bash
export CONTEXT_FIXER_ROOT="/Users/cY/dev/skills/cy-codex-skills/dev/tools/context-fixer"
```

Prefer the installed console script when available:

```bash
context-fixer --repo .
```

If `context-fixer` is not on `PATH`, use the checkout directly:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$CONTEXT_FIXER_ROOT/src" \
/opt/homebrew/bin/python3.11 -m context_fixer --repo .
```

## Default Workflow

1. Run the audit from the target repository root.
2. Keep the text output in chat concise: severity, policy status, peak context,
   compactions seen, top contributors, and recommendations.
3. If the user wants a file artifact, generate HTML under a local report path.
4. Report remaining risks clearly, especially global activation findings that
   should not be changed without explicit approval.

Recommended command:

```bash
export CONTEXT_FIXER_ROOT="/Users/cY/dev/skills/cy-codex-skills/dev/tools/context-fixer"
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$CONTEXT_FIXER_ROOT/src" \
/opt/homebrew/bin/python3.11 -m context_fixer --repo .
```

HTML report:

```bash
export CONTEXT_FIXER_ROOT="/Users/cY/dev/skills/cy-codex-skills/dev/tools/context-fixer"
mkdir -p .context-fixer
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$CONTEXT_FIXER_ROOT/src" \
/opt/homebrew/bin/python3.11 -m context_fixer --repo . --html .context-fixer/report.html
```

JSON report:

```bash
export CONTEXT_FIXER_ROOT="/Users/cY/dev/skills/cy-codex-skills/dev/tools/context-fixer"
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$CONTEXT_FIXER_ROOT/src" \
/opt/homebrew/bin/python3.11 -m context_fixer --repo . --json
```

Request trace:

```bash
export CONTEXT_FIXER_ROOT="/Users/cY/dev/skills/cy-codex-skills/dev/tools/context-fixer"
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$CONTEXT_FIXER_ROOT/src" \
/opt/homebrew/bin/python3.11 -m context_fixer --repo . --trace .traces/codex-request.jsonl
```

## Interpretation

- `green`: context policy is healthy.
- `yellow`: monitor context growth and checkpoint timing.
- `orange`: recommend durable checkpoint and compaction soon.
- `red`: checkpoint before continuing large work.

Large runtime tool output is usually actionable: save verbose output to files,
read targeted excerpts, or summarize instead of replaying full logs into chat.

Global plugin or skill findings are audit findings, not automatic cleanup
permission. Ask before disabling or deleting global Codex configuration.
