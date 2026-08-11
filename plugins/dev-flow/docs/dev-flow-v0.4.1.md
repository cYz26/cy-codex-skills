# DevFlow 0.4.1

DevFlow 0.4.1 fixes migration and Stop Hook startup on hosts where the Hook
manifest's `python3` resolves to Python 3.9 and the standard-library `tomllib`
module is unavailable.

Legacy workflow TOML inspection remains fail-closed: when no
standards-compliant TOML parser is available, a configuration that references a
retired workflow requires manual review and cannot become an automatic cleanup
candidate. Unrelated TOML files do not create false blockers.

This patch changes no Hook response schema, dependency, project configuration
schema, migration step, or cleanup authority. Project schema remains 8 and the
managed refresh contract advances to revision 12.
