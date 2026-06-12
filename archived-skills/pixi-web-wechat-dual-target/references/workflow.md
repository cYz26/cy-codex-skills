# Web WeChat Dual-Target Workflow

Use this reference when a PixiJS project already has, or is actively building toward, both Web and WeChat outputs.

## Entry Rule

If the platform boundary is still unclear, run `$pixi-mini-game-readiness` first. Use this skill after readiness rules already exist or while enforcing them during ongoing development.

## Change Classification

Classify each task as:
1. pure shared logic
2. shared runtime or scene change
3. platform bridge or lifecycle change
4. asset, font, text-rendering, or packaging change
5. project-rule or documentation change

## Execution Order

For implementation work:
1. identify which target-specific layers may change
2. keep shared modules free of target-specific APIs
3. isolate any workaround in platform or build layers
4. for packaging or text-asset work, ensure the normal target build commands regenerate any packaged atlas or mirrored asset output automatically before target builds
5. when a project ships Chinese through a fixed-copy glyph atlas, add a regression test that scans current source copy and fails if the atlas is missing any required glyphs
6. run the matching validation matrix from `gates.md`
7. run the matching smoke flow from `smoke-checklist.md`

## Review Order

For review work:
1. check shared-layer neutrality first
2. check asset and lifecycle policy second
3. check validation coverage third
4. report any target that remains unverified
