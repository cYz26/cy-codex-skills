## 1. Governance Model Tests

- [x] 1.1 Add failing tests requiring `report["governance"]` with profile,
  AGENTS, Skills, MCP, hook, and command-output recommendations.
- [x] 1.2 Add failing tests proving governance output omits sensitive bodies.

## 2. Governance Implementation

- [x] 2.1 Create `src/context_fixer/governance.py` with grouped advisory
  recommendation builders.
- [x] 2.2 Wire governance generation into `analyze_context` without removing
  existing report keys.
- [x] 2.3 Ensure every recommendation includes priority, surface, reason,
  action, and evidence.

## 3. Rendering and CLI

- [x] 3.1 Render governance recommendations in text and Markdown.
- [x] 3.2 Render governance recommendations in HTML and dashboard data.
- [x] 3.3 Include governance recommendations in `recommend` output.

## 4. Documentation

- [x] 4.1 Document advisory governance behavior in README.
- [x] 4.2 Update `skills/context-fixer/SKILL.md`.

## 5. Verification

- [x] 5.1 Run targeted governance tests.
- [x] 5.2 Run full unit tests and py_compile.
