## MODIFIED Requirements

### Requirement: Plugin Eval findings are systematically reassessed
The change SHALL record a fresh systematic Plugin Eval assessment after
implementation, and Plugin Eval findings SHALL be remediated by default before
completion unless an explicit deferral exception applies.

#### Scenario: Final evaluation is performed
- **WHEN** implementation is complete
- **THEN** Plugin Eval is run for the release plugin root
- **AND** Plugin Eval is run for the development plugin root
- **AND** the final report calls out remaining warnings, if any, with concrete follow-up recommendations

#### Scenario: Plugin Eval reports actionable findings
- **WHEN** Plugin Eval reports failures, warnings, or fix-first recommendations
- **THEN** the workflow fixes or optimizes the findings by default before completion
- **AND** reruns Plugin Eval or records why rerunning is not applicable

#### Scenario: Plugin Eval finding is deferred
- **WHEN** a Plugin Eval finding is not fixed in the current change
- **THEN** verification evidence records the deferral reason, residual risk, and concrete follow-up path
- **AND** the reason is one of out-of-scope work, destructive or risky change, dependency or architecture decision, or required user approval
