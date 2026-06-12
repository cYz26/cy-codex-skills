# 60-decoupling.md - Decoupling Rules (signals / groups / autoload)

## 1) Signals as Default

Use signals for event-driven communication when logic crosses scene boundaries.

Trigger conditions:
1. You are about to use `get_parent()` for control flow.
2. You are about to hard-code fragile paths like `get_node("../..")`.
3. Child node behavior depends on fixed tree depth.

## 2) Groups for Broadcast

Use groups for one-to-many operations (for example freeze/unfreeze, alert mode, state refresh).

Example:

```gdscript
get_tree().call_group("guards", "enter_alert_mode")
```

## 3) Autoload for Focused Global Services

Use autoload for cross-scene services only (audio, save/load, scene transitions, global config).

Avoid:
1. Stuffing feature logic into one giant autoload (God Object).
2. Freeing autoload nodes at runtime.

## 4) Review Checklist

1. Events -> signals
2. Broadcast -> groups
3. Global service -> autoload (single responsibility)
4. Reject hard path coupling for core gameplay logic
