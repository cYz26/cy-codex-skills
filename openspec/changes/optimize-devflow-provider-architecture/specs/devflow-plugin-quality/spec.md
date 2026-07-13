## MODIFIED Requirements

### Requirement: Plugin Eval findings are systematically reassessed
DevFlow SHALL treat the release plugin package as the primary Plugin Eval
release-readiness target, use the development root only as a diagnostic source
quality check, and record static-budget plus observed-usage evidence or an
explicit blocker.

#### Scenario: Final release evaluation is performed
- **WHEN** implementation and release synchronization are complete
- **THEN** Plugin Eval is run for the release plugin root
- **AND** the score is not below the recorded `86/B` baseline, there are zero failures, no new warning identifiers, and risk is no higher than medium
- **AND** every remaining finding records its fix or deferral reason, residual risk, and follow-up path

#### Scenario: Development source is evaluated diagnostically
- **WHEN** source-quality diagnosis is useful before release synchronization
- **THEN** Plugin Eval may run against the development plugin root
- **AND** that result does not replace the release-target readiness signal

#### Scenario: Static budget is used for an optimization claim
- **WHEN** the change claims reduced DevFlow context or invocation cost
- **THEN** release-target static active/deferred budget is compared with the captured baseline
- **AND** observed usage is attached or the missing telemetry blocker prevents an outcome-efficiency claim
