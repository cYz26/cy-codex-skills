# 80-release-policy.md - Version and Support Policy

## Principles

1. Respect repository-locked engine version unless upgrade is explicitly requested.
2. Within a minor series, prefer latest patch before deep debugging.
3. Use supported branches for active development whenever possible.

## Default Recommendation

If repository does not lock version, recommend `Godot 4.6.x`.

## Upgrade Safety

When performing version upgrade:
1. Include migration notes
2. Re-run validation chain
3. Test core gameplay path and export path
