# Web and WeChat Smoke Checklist

Use the smallest checklist that still matches the risk of the change.

## Web Smoke

Verify:
1. cold start reaches the first interactive scene
2. critical assets load without visible errors
3. one representative gameplay loop still works
4. resize or reload does not duplicate listeners or corrupt state

## WeChat Smoke

Verify in WeChat DevTools:
1. cold start reaches the first interactive scene
2. assets resolve without path failures
3. Chinese labels or other packaged text assets render visibly without missing-glyph squares where shipping copy should exist
4. touch input still works
5. background and foreground lifecycle does not corrupt state
6. saved progress survives a relaunch when the changed code touches persistence

## Report

After smoke testing, report:
1. which checklist ran
2. what was skipped
3. what remains unverified
