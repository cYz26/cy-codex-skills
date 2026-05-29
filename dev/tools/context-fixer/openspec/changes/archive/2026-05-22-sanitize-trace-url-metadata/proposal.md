## Why

While testing Context Fixer against `app_ai_doctor`, a supplied request trace
showed that `request_path` metadata could retain URL query strings. Query
strings can contain API keys, tokens, version selectors, or other sensitive
parameters, so sanitized reports must omit them everywhere.

## What Changes

- Strip query strings and fragments from request trace `request_path` metadata.
- Strip query strings and fragments from URL-like trace endpoint and upstream
  metadata while preserving useful origin/path context.
- Add a regression test proving serialized reports do not include sensitive
  query parameters.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: clarify sanitized reporting for URL metadata in request
  trace summaries, timeline, activity, dashboard, and persisted snapshots.

## Impact

- Affected code: `src/context_fixer/trace.py`.
- Affected tests: `tests/test_context_fixer.py`.
- Public behavior: trace URL metadata remains useful but no longer includes
  query strings or fragments.
- Dependencies: none.
