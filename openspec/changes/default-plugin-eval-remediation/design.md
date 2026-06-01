## Context

The repository now has a Plugin Eval Gate for plugin and skill changes, and
verification evidence records scores, findings, and optimization decisions. The
current wording still allows agents to stop after evaluation by choosing to
record a deferral. The new policy should bias execution toward fixing findings
without removing the ability to defer genuinely unsafe or out-of-scope work.

## Goals / Non-Goals

**Goals:**

- Make remediation-first behavior explicit in root and generated project
  instructions.
- Preserve a narrow, auditable deferral path for findings that should not be
  fixed automatically.
- Keep the rule concise enough that it remains useful in `AGENTS.md` and
  templates.
- Add tests for the exact policy terms that matter.

**Non-Goals:**

- Automatically mutate files from the Plugin Eval tool itself.
- Require broad packaging refactors every time Plugin Eval reports a large
  deferred-budget risk.
- Remove user approval requirements for destructive, architectural, dependency,
  or scope-expanding changes.
- Change Plugin Eval's own scoring algorithm.

## Decisions

- **Policy location:** Put the rule in root `AGENTS.md` for this repository and
  both DevFlow `AGENTS.md` templates for generated projects. This keeps behavior
  visible to agents before work starts.
- **Spec location:** Modify `devflow-plugin-quality` because it already owns
  Plugin Eval reassessment for DevFlow release quality.
- **Default action:** Use "default to fixing/optimizing" language rather than
  "must fix everything" so agents still obey scope, safety, and approval gates.
- **Deferral evidence:** Require reason, residual risk, and follow-up path so a
  deferral is an accountable exception rather than a shortcut.
- **Testing:** Extend the existing Plugin Eval gate test instead of adding a
  separate brittle test for every sentence.

## Risks / Trade-offs

- **Risk: Agents expand scope to chase every Plugin Eval finding.** Mitigation:
  list concrete deferral exceptions and require follow-up evidence.
- **Risk: Agents skip remediation by calling everything deferred.** Mitigation:
  make deferral an exception and test for remediation-first wording.
- **Risk: Policy text becomes too verbose.** Mitigation: keep `AGENTS.md`
  concise and put nuance in the OpenSpec design/spec.
