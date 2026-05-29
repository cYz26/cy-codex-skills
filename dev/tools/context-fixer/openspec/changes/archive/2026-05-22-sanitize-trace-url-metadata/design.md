## Context

Context Fixer already omits prompt bodies, message bodies, tool argument bodies,
tool output bodies, file content bodies, trace payload bodies, and authorization
headers. Request trace URL metadata is still rendered in summaries and dashboard
projections, so it must be sanitized as metadata, not treated as harmless text.

## Decision

Normalize URL-like metadata at trace parse time:

- `request_path` is stored as a path only, without query string or fragment.
- endpoint and upstream URL metadata preserve scheme, host, and path, but omit
  query string and fragment.
- timeline and activity events continue using path-only metadata.

This keeps reports actionable for endpoint attribution while preventing
sensitive query parameters from reaching text, JSON, HTML, dashboard, or stored
history snapshots.

## Alternatives Considered

- Redact only known query parameter names: rejected because unknown vendor
  parameters can be sensitive.
- Drop all URL metadata: rejected because endpoint grouping is useful for
  request trace attribution and governance recommendations.

## Verification

- Add a regression test with a trace path and upstream URL containing a sentinel
  query secret.
- Run the targeted test, full unit suite, py_compile, and strict OpenSpec
  validation.
