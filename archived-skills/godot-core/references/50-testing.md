# 50-testing.md - Testing with GUT and Smoke Baseline

## Minimum Baseline

1. If unit tests do not exist, keep `tools/smoke_test_runner.gd` runnable.
2. If unit tests exist, default test location is `res://tests/`.

## GUT CLI Example (Godot 4.x)

```bash
godot --headless -s res://addons/gut/gut_cmdln.gd --path "$PWD" -gdir=res://tests -ginclude_subdirs -gexit
```

## JUnit Output (Optional for CI)

Use `-gjunit_xml_file=<path>` to export JUnit XML (for example `build/test-results/gut-junit.xml`).

## Required Reporting

Always report:
1. Command actually run
2. Pass/fail summary
3. What is not covered by test execution
