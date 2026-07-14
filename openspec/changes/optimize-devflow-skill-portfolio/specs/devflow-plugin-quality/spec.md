## MODIFIED Requirements

### Requirement: Plugin Eval findings are systematically reassessed
The change SHALL record a fresh systematic assessment using the release-preferred
DevFlow plugin as the primary target and the development plugin as a diagnostic
target.

#### Scenario: Final evaluation is performed
- **WHEN** implementation and release synchronization are complete
- **THEN** `sync_release_assets.py --eval-target` resolves the release plugin
- **AND** Plugin Eval is run for the release plugin root
- **AND** Plugin Eval is run for the development plugin root
- **AND** the release result has zero failures and a score no lower than 86/B
- **AND** release invoke cost is no greater than 10,000 tokens
- **AND** the final report records before/after trigger, invoke, deferred,
  explicit-only, and total budgets plus every remaining warning.

## ADDED Requirements

### Requirement: Skill portfolio release assets remain synchronized
DevFlow SHALL verify that source skill changes, removed supporting resources,
new references, the dependency catalog, the project-migration manifest, and the
generated release package describe one coherent public portfolio.

#### Scenario: Release promotion completes
- **WHEN** the DevFlow release promotion gate runs after skill optimization
- **THEN** generated release assets contain the same public skill set and
  supporting-resource contract as the development source
- **AND** a second promotion check reports `current`
- **AND** packaged and runtime verification pass without stale managed outputs.
