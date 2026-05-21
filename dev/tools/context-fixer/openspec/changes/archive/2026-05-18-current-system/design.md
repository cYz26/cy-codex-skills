# Design: Current System Baseline

## Approach

Treat this as a brownfield baseline change. The implementation already exists
under `src/context_fixer`, with `src/codex_context_lens` retained for
compatibility. This change documents the current behavior, verifies it, and
keeps archive blocked until the baseline is approved.

## Data Flow

1. CLI arguments select a target repository, optional working directory,
   optional session JSONL, optional request trace JSONL, and output format.
2. Session parsing extracts telemetry, model context window, compaction events,
   and estimated runtime contributors without returning sensitive bodies.
3. Optional trace parsing extracts request/response usage and request shape from
   user-supplied trace files.
4. Static source scanning inspects project/global Codex configuration,
   instruction chains, project-local skills, and workflow signals.
5. The analyzer combines exact usage where available with estimated
   attribution, policy status, findings, and recommendations.
6. Renderers produce text, JSON, or self-contained HTML output without printing
   prompt, message, tool argument, or tool output bodies.

## Compatibility

Do not change CLI entry points, output privacy guarantees, or the
`codex-context-lens` compatibility alias without a future approved change.

## Testing

Use the existing unit suite as the baseline verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.11 -m unittest discover -s tests -v`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /opt/homebrew/bin/python3.11 -m context_fixer --repo . --latest-sessions 1`

Record fresh command results in `.planning/phases/01-foundation/VERIFICATION.md`
before archive.
