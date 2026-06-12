# Pixi Official Docs Policy

Use Pixi's official LLM docs as the first source of truth for API facts.

## Read Order

1. `https://pixijs.com/llms.txt`
   - Use for fast navigation and deciding which guide or API surface matters.
2. `https://pixijs.com/llms-medium.txt`
   - Use for common implementation patterns and mid-sized context windows.
3. `https://pixijs.com/llms-full.txt`
   - Use when you need exact class, method, option, or event details.

## Source-of-Truth Rules

1. If Pixi API behavior in community posts conflicts with the LLM docs, trust the official LLM docs.
2. If the LLM docs describe an API but not the engineering tradeoff, cross-check the official guides next.
3. If the repo is pinned to an older Pixi version, respect the repo version over generic v8 assumptions.

## When to Load Other Official Pixi Docs

Use the regular guides after the LLM docs when you need:
1. application boot patterns
2. assets loading strategy
3. federated events and input handling
4. rendering and performance tradeoffs

Recommended follow-up sources:
1. `https://pixijs.com/8.x/guides/components/application`
2. `https://pixijs.com/8.x/guides/components/assets`
3. `https://pixijs.com/8.x/guides/components/events`
4. `https://pixijs.com/8.x/guides/concepts/performance-tips`

## Practical Agent Workflow

1. Start with `llms.txt` to narrow the surface area.
2. Read `llms-medium.txt` before drafting a new subsystem or code sample.
3. Escalate to `llms-full.txt` only for exact API validation.
4. Summarize the chosen API in local project terms instead of pasting long excerpts.
