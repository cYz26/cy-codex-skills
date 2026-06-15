## Why

`lark-feishu-ops` currently says FeishuOps may lazy-read official `lark-*` guidance, but it does not produce an explicit, testable handoff that tells a subagent which domain guidance sources are available for a specific Lark action. Making guidance selection explicit improves complex Lark calls without globally activating every official Lark skill in the main agent.

## What Changes

- Add a domain guidance resolver for FeishuOps requests.
- Map common FeishuOps actions to candidate official `lark-*` domain skills.
- Add CLI help/schema fallback metadata when no matching skill file is available.
- Include `guidance_sources` in prepared FeishuOps handoff requests and require FeishuOps output to report the sources it used.
- Update skill docs, runtime prompt, protocol reference, README, and tests.
- Keep `lark-cli` as the execution channel; injected domain skills are guidance, not the platform API.

## Capabilities

### New Capabilities

- `lark-feishu-ops-guidance`: Defines how FeishuOps selects, injects, and reports Lark domain guidance sources for subagent work.

### Modified Capabilities

- None.

## Impact

- Updates `plugins/lark-feishu-ops` source, tests, and OpenSpec artifacts.
- May refresh the installed `lark-feishu-ops@cy-codex-skills` plugin cache after source changes.
- Does not globally activate official `lark-*` skills.
- Does not install official Lark skills or change `lark-cli` authentication.
