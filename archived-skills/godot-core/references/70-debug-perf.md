# 70-debug-perf.md - Debugger Evidence Protocol

Apply this protocol for FPS drops, stutters, memory spikes, resource leaks, and rendering issues.

## Mandatory Evidence Output

1. Deterministic reproduction steps
2. Observations from Godot Debugger:
   - Monitors (FPS, memory, node count, and related counters)
   - Video RAM usage and top offenders
3. Before/after comparison with at least one measurable metric pair

## Optimization Order

1. Remove redundant work
2. Reduce frequency or batch work
3. Replace algorithm/data structure when needed
4. Re-measure in same scenario
