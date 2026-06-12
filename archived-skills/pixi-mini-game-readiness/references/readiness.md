# Pixi Mini-Game Readiness Workflow

Use this reference when auditing a Web-first Pixi project for future WeChat or Douyin mini-game migration.

## Core Principle

Start setting dual-target rules during the audit, not after implementation starts.

The audit output must identify:
1. what is already safe
2. what must be refactored now
3. what future contributors are no longer allowed to reintroduce

## Audit Dimensions

Review these dimensions:
1. runtime coupling
2. asset and loading policy
3. input and interaction model
4. lifecycle handling
5. persistence and network access
6. UI composition
7. packaging assumptions
8. future dual-target workflow and validation gates

## Severity Model

Classify findings as:
1. `blocker`: rewrite required before migration can realistically start
2. `high-risk`: migration is possible, but current shape will cause significant future rewrite or regression cost
3. `watch`: acceptable for now only if isolated and documented as a temporary compromise

## Typical Blockers

Flag these first:
1. gameplay logic importing `window` or `document`
2. scene logic depending on HTML layout for core interactions
3. persistence hardcoded to browser storage APIs
4. raw networking embedded inside scenes
5. hidden lifecycle behavior attached to DOM visibility or focus events
6. hardcoded asset roots or browser path assumptions spread through gameplay code
7. platform-specific branches copied across scenes or systems

## No-Regression Constraints to Record

At audit time, lock rules such as:
1. platform globals may appear only inside dedicated platform wrappers
2. asset path policy belongs in manifest or resolver layers
3. gameplay-critical UI stays canvas-first
4. lifecycle wiring belongs in boot or platform modules
5. shared logic and systems must remain runnable without browser globals

## Recommended Remediation Order

1. isolate platform services
2. normalize input and launch context
3. replace raw asset paths with manifests or resolvers
4. move lifecycle handling into boot or platform modules
5. reduce gameplay-critical DOM dependencies
6. define future validation gates before more features land

## Audit Deliverable Template

Produce:
1. readiness level
2. blocker list
3. high-risk list
4. watch list
5. proposed boundary contracts
6. explicit no-regression constraints for future contributors
7. safe short-term compromises
8. what must be re-verified against official vendor docs later

If the repository will continue active Web development while mini-game support remains pending, hand off to `$pixi-web-wechat-dual-target`.
