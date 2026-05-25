## Why

Current reports emphasize aggregate totals and the latest usage snapshot, which can mislead when recent test or interrupted sessions do not represent the real pressure point. Context Fixer needs a chronological view so users can identify when context grew, when compaction occurred, and which session or request caused the peak.

## What Changes

- Add sanitized timeline analysis to reports, combining session token events, compaction events, and request trace events.
- Distinguish latest state, peak state, growth jumps, compaction history, and abnormal or incomplete sessions.
- Render timeline evidence in JSON, text, and HTML without exposing prompt bodies, tool arguments, tool outputs, auth headers, or trace payload bodies.
- Add recommendations that explicitly point users to timeline-based diagnosis when history contradicts the latest snapshot.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `current-system`: Add chronological context timeline requirements for session and request trace analysis.

## Impact

- Affected code: `src/context_fixer/session.py`, `src/context_fixer/trace.py`, `src/context_fixer/analyzer.py`, `src/context_fixer/render.py`, and tests.
- Affected APIs: the JSON report gains a new top-level sanitized `timeline` object and additional diagnosis fields for latest valid usage and peak event attribution.
- Dependencies: no new production dependency.
